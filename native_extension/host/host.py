#!/usr/bin/env python3
import sys
import json
import struct
import threading
import os
import yt_dlp
import traceback
import logging
logging.basicConfig(filename="/tmp/ytdl_native_host.log", level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
logging.debug("Host started")

def read_message():
    """
    Reads a message from Chrome's Native Messaging format.
    Chrome sends a 32-bit (4-byte) integer indicating the message length,
    followed by the JSON-encoded message string.
    """
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        sys.exit(0)
    msg_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(msg_length).decode('utf-8')
    return json.loads(message)

def send_message(msg_dict):
    """
    Sends a message back to Chrome using Native Messaging.
    We pack the message length as a 4-byte string prior to the JSON payload.
    """
    message = json.dumps(msg_dict)
    encoded_message = message.encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded_message)))
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

def download_hook(d):
    """
    yt-dlp progress hook injected into the download process.
    Instantly streams percentages and speeds back to the browser via stdout.
    """
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', '0MiB/s').strip()
        # Clean up ANSI escape strings if they exist
        percent = percent.replace('\x1b[0;94m', '').replace('\x1b[0m', '')
        speed = speed.replace('\x1b[0;32m', '').replace('\x1b[0m', '')
        send_message({
            "action": "download_progress",
            "percent": percent,
            "speed": speed
        })
    elif d['status'] == 'finished':
        send_message({
            "action": "download_finished",
            "filename": os.path.basename(d.get('filename', 'Unknown_File'))
        })

def format_size(bytes_size):
    if not bytes_size: return "Unknown Size"
    return f"{bytes_size / (1024 * 1024):.1f} MB"

def get_formats(url):
    """Fetches video format metadata without downloading."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'noplaylist': True,
        # Notice: No hardcoded 'http_headers'. 
        # This forces yt-dlp to natively handle PO Tokens and avoid 403 Forbidden errors.
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We don't cache this extraction globally. This cleanly prevents
            # crashes related to process_ie_result stale dictionaries later.
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Find best audio size for estimating combined sizes
            best_audio = next((f for f in reversed(formats) if f.get('vcodec') == 'none' and f.get('acodec') != 'none'), None)
            audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
            if audio_size == 0 and best_audio:
                # Estimate from tbr (Total Bitrate)
                tbr = best_audio.get('tbr') or best_audio.get('abr') or 0
                duration = info.get('duration') or 0
                audio_size = int((tbr * 1000 / 8) * duration)

            resolutions = [1080, 720, 480, 360]
            available_qualities = []
            
            # We want one option per resolution.
            # Best video at that height.
            for res in resolutions:
                # Get videos with this exact height
                res_formats = [f for f in formats if f.get('height') == res and f.get('vcodec') != 'none' and f.get('ext') in ('mp4', 'webm')]
                if not res_formats:
                    continue
                # Pick the one with the best quality (usually highest tbr)
                best_vid = max(res_formats, key=lambda f: f.get('tbr') or 0)
                vid_size = best_vid.get('filesize') or best_vid.get('filesize_approx') or 0
                
                if vid_size == 0:
                    tbr = best_vid.get('tbr') or best_vid.get('vbr') or 0
                    duration = info.get('duration') or 0
                    vid_size = int((tbr * 1000 / 8) * duration)
                
                total_size = vid_size
                # If the video format doesn't have audio, add our estimated audio size
                if best_vid.get('acodec') == 'none':
                    total_size += audio_size
                
                # format_id will just be a standard yt-dlp selector to let yt-dlp do the heavy lifting safely
                format_id = f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best'
                
                available_qualities.append({
                    'label': f'{res}p',
                    'size': format_size(total_size) if total_size > 0 else 'Unknown Size',
                    'format': format_id
                })
                
            # Add audio-only option
            available_qualities.append({
                'label': 'Audio Only',
                'size': format_size(audio_size) if audio_size > 0 else 'Unknown Size',
                'format': 'bestaudio[ext=m4a]/bestaudio/best'
            })
            
            send_message({
                "action": "formats_ready", 
                "title": info.get('title'),
                "qualities": available_qualities
            })
    except Exception as e:
        logging.error(f"Exception: {traceback.format_exc()}")
        send_message({"action": "error", "error": f"Format extraction failed: {str(e)}"})

def download_video(url, format_str):
    """Executes the actual video download."""
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    
    ydl_opts = {
        'format': format_str,
        'progress_hooks': [download_hook],
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': True,
        # Notice: No hardcoded 'http_headers'. PO Tokens are preserved.
    }
    
    try:
        # A 100% fresh fallback extraction occurs inside ydl.download() here,
        # preventing mapping crashes or cache pollution.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logging.error(f"Exception: {traceback.format_exc()}")
        send_message({"action": "error", "error": f"Download failed: {str(e)}"})

def main():
    """
    Main loop keeping the native host process alive to actively listen
    for incoming stdout buffers from the Chrome Extension.
    """
    while True:
        try:
            msg = read_message()
            action = msg.get("action")
            url = msg.get("url")
            
            if action == "get_formats":
                # Spawning threads prevents the stdout read loop from blocking
                threading.Thread(target=get_formats, args=(url,), daemon=True).start()
                
            elif action == "download":
                fmt = msg.get("format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best")
                threading.Thread(target=download_video, args=(url, fmt), daemon=True).start()
                
        except json.JSONDecodeError:
            continue
        except SystemExit:
            break
        except BaseException as e:
            logging.error(f"Critical Native Host Crash: {traceback.format_exc()}")
            send_message({"action": "error", "error": f"Critical Native Host Crash: {str(e)}"})
            sys.exit(1)

if __name__ == '__main__':
    main()

