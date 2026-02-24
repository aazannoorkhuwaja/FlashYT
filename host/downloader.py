import json
import os
import re
import subprocess
import sys
import platform
import shutil

from logger import log
from cookies import get_best_available_cookies, cleanup_cookie_dir

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def get_ytdlp_path():
    """
    Returns absolute path to bundled yt-dlp.exe
    Checks: same directory as host.exe (PyInstaller bundle)
            or relative path ../vendor/yt-dlp.exe (script)
    Raises FileNotFoundError with clear message if not found.
    """
    executable_name = 'yt-dlp.exe' if platform.system() == 'Windows' else 'yt-dlp'
    
    # 1. Check if running as compiled PyInstaller executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, executable_name)
        if os.path.exists(bundle_path):
            return bundle_path
            
    # 2. Check vendor/ directory when running from source
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vendor_path = os.path.join(os.path.dirname(script_dir), "vendor", executable_name)
    if os.path.exists(vendor_path):
        return vendor_path
        
    # 3. Check system PATH as fallback
    system_path = shutil.which("yt-dlp")
    if system_path:
        return system_path
        
    raise FileNotFoundError("yt-dlp not found. Please reinstall the downloader.")

def get_ffmpeg_path():
    """
    Returns absolute path to bundled ffmpeg.exe
    Same logic as get_ytdlp_path()
    """
    executable_name = 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg'
    
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, executable_name)
        if os.path.exists(bundle_path):
            return bundle_path
            
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vendor_path = os.path.join(os.path.dirname(script_dir), "vendor", executable_name)
    if os.path.exists(vendor_path):
        return vendor_path
        
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
        
    raise FileNotFoundError("ffmpeg not found. Please reinstall the downloader.")

def prefetch_qualities(url, cookies_browser=None):
    """
    Runs: yt-dlp --dump-json --no-playlist [url]
    Returns list of formats or error dict.
    """
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--dump-json",
        "--ignore-config",
        "--no-warnings",
        url
    ]
    
    log.debug(f"[Downloader] prefetch_qualities running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode != 0:
            err = result.stderr.strip()
            log.error(f"[Downloader] prefetch_qualities failed (Code {result.returncode}): {err}")
            
            # Extract human readable error
            msg = "Failed to fetch video details."
            for line in err.split('\n'):
                if 'ERROR:' in line:
                    msg = line.split('ERROR:', 1)[1].strip()
                    break
            return {"type": "error", "message": msg}
            
        try:
            info = json.loads(result.stdout)
            
            formats_data = info.get('formats', [])
            duration = info.get('duration', 0)
            
            # Evaluate best audio
            audio_formats = [f for f in formats_data if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0) if audio_formats else None
            
            audio_filesize = 0
            if best_audio:
                audio_filesize = best_audio.get('filesize') or best_audio.get('filesize_approx')
                if not audio_filesize:
                    abr = best_audio.get('abr') or best_audio.get('tbr') or 128
                    audio_filesize = int(abr * 1024 * duration / 8)
                audio_filesize = audio_filesize or 0
                
            # Deduplicate video heights keeping the highest quality MP4
            video_resolutions = {}
            for f in formats_data:
                height = f.get('height')
                if not height or f.get('vcodec') == 'none':
                    continue
                
                v_filesize = f.get('filesize') or f.get('filesize_approx')
                if not v_filesize:
                    vbr = f.get('vbr') or f.get('tbr')
                    if not vbr:
                        bitrates = {2160: 15000, 1440: 8000, 1080: 4000, 720: 2000, 480: 1000, 360: 700, 240: 400, 144: 200}
                        vbr = bitrates.get(height, 2000)
                    v_filesize = int(vbr * 1024 * duration / 8) if duration else 0
                v_filesize = v_filesize or 0
                
                ext = f.get('ext', '')
                is_better = False
                
                if height not in video_resolutions:
                    is_better = True
                else:
                    old = video_resolutions[height]
                    if ext == 'mp4' and old['ext'] != 'mp4':
                        is_better = True
                    elif ext == old['ext'] and (v_filesize + audio_filesize) > (old['size_mb'] * 1024 * 1024):
                        is_better = True
                
                if is_better:
                    video_resolutions[height] = {
                        'label': f"{height}p",
                        'itag': f"{height}",
                        'ext': ext,
                        'size_mb': round((v_filesize + audio_filesize) / (1024 * 1024), 1)
                    }
                    
            # Sort qualities dynamically (Highest first)    
            sorted_vids = sorted(video_resolutions.values(), key=lambda x: int(x['label'].replace('p', '')), reverse=True)
            
            # Format outputs exactly like the spec requires
            qualities = []
            for v in sorted_vids:
                qualities.append({
                    "label": v['label'],
                    "itag": int(v['itag']), # Spec demands int 137, 22 etc if possible, but we use height for simplicity selector
                    "size_mb": v['size_mb']
                })
                
            if best_audio:
                qualities.append({
                    "label": "Audio Only (MP3)",
                    "itag": "audio",
                    "size_mb": round(audio_filesize / (1024 * 1024), 1)
                })
                
            return {
                "type": "prefetch_result",
                "title": info.get('title', 'YouTube Video'),
                "qualities": qualities
            }
            
        except json.JSONDecodeError:
            log.error("[Downloader] Failed to decode yt-dlp JSON.")
            return {"type": "error", "message": "Failed to parse video info from YouTube."}
            
    except Exception as e:
        log.exception(f"[Downloader] prefetch_qualities encountered Python exception: {e}")
        return {"type": "error", "message": str(e)}

def _build_video_format_string(max_height):
    h = max_height
    return (
        f"bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/"
        "bestvideo+bestaudio/"
        "best/"
        "bestvideo/"
        "bestaudio"
    )

def download_video(url, itag, output_dir, progress_callback, cookies_browser=None):
    """
    Downloads the video and streams progress lines natively back.
    """
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--ffmpeg-location", get_ffmpeg_path(),
        "--ignore-config",
        "--newline", 
        "--no-warnings",
        "-o", os.path.join(output_dir, "%(title)s.%(ext)s"),
    ]
    
    # Process Cookie Injection
    cookie_dict = get_best_available_cookies()
    if cookie_dict:
        if "profile_dir" in cookie_dict:
            cmd.extend(["--cookies-from-browser", f"{cookie_dict['browser']}:{cookie_dict['profile_dir']}"])
        else:
            cmd.extend(["--cookies-from-browser", cookie_dict['browser']])
        
    # Analyze format to build selector sequence
    if itag == "audio":
        cmd.extend([
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3"
        ])
    else:
        try:
            h = int(itag)
        except:
            h = 1080
        cmd.extend([
            "-f", _build_video_format_string(h),
            "--merge-output-format", "mp4",
            "--write-subs",
            "--sub-langs", "en,all",
            "--embed-subs"
        ])
    
    cmd.append(url)
    log.debug(f"[Downloader] download_video running: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )
    
    # yt-dlp Output parser regex: [download] 100% of 23.41MiB in 00:03 at 7.64MiB/s or ETA
    progress_regex = re.compile(r'\[download\]\s+(.*?%)\s+of\s+.*?(?:at\s+(.*?/s))?\s+(?:ETA\s+(.*?))?(?:\s+in\s+.*?)?$')
    destination_regex = re.compile(r'\[(?:download|Merger|ExtractAudio)\]\s+Destination:\s+(.*)')
    already_downloaded_regex = re.compile(r'\[download\]\s+(.*)\s+has already been downloaded')
    
    last_filename = ""
    
    try:
        for line in iter(process.stdout.readline, ''):
            clean_line = ansi_escape.sub('', line).strip()
            if not clean_line:
                continue
                
            dest_match = destination_regex.search(clean_line)
            if dest_match:
                last_filename = os.path.basename(dest_match.group(1))
                continue
                
            already_match = already_downloaded_regex.search(clean_line)
            if already_match:
                last_filename = os.path.basename(already_match.group(1))
                progress_callback({
                    "type": "progress",
                    "percent": "100%",
                    "speed": "Done",
                    "eta": ""
                })
                continue
                
            prog_match = progress_regex.search(clean_line)
            if prog_match:
                percent = prog_match.group(1).strip()
                speed = (prog_match.group(2) or "").strip()
                eta = (prog_match.group(3) or "").strip()
                
                progress_callback({
                    "type": "progress",
                    "percent": percent,
                    "speed": speed,
                    "eta": eta
                })
        
        process.stdout.close()
        process.wait()
        
        cleanup_cookie_dir(cookie_dict)
        
        if process.returncode != 0:
            stderr_out = process.stderr.read()
            log.error(f"[Downloader] download_video failed (Code {process.returncode}): {stderr_out}")
            
            msg = "yt-dlp encountered an error during download."
            for err_line in stderr_out.split('\n'):
                if 'ERROR:' in err_line:
                    msg = err_line.split('ERROR:', 1)[1].strip()
                    break
            return {"type": "error", "message": msg}

        if not last_filename:
            log.warning("[Downloader] Finished but could not accurately determine the filename from logs.")
            # If no extraction log matched, fall back to searching for latest file in output_dir
            return {"type": "error", "message": "Failed to verify completion file destination."}
            
        final_path = os.path.join(output_dir, last_filename)
        size_mb = 0.0
        if os.path.exists(final_path):
            size_mb = round(os.path.getsize(final_path) / (1024 * 1024), 1)

        log.info(f"[Downloader] ✓ Job Complete: {final_path}")
        return {
            "type": "done",
            "filename": last_filename,
            "size_mb": size_mb,
            "path": final_path
        }
            
    finally:
        if process.poll() is None:
            process.kill()
