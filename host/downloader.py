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

def _find_executable(name):
    """
    Shared executable resolver. Lookup order:
      1. Persistent auto-update AppData dir (overrides everything)
      2. PyInstaller bundle (_MEIPASS)
      3. ../vendor/ relative to source
      4. System PATH
    """
    executable_name = f"{name}.exe" if platform.system() == 'Windows' else name

    # 1. Check persistent auto-update directory (overrides bundle)
    appdata = os.environ.get('APPDATA', '') or os.path.expanduser('~')
    updated_path = os.path.join(appdata, 'YouTubeNativeExt', executable_name)
    if os.path.exists(updated_path):
        return updated_path

    # 2. PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_path = os.path.join(sys._MEIPASS, executable_name)
        if os.path.exists(bundle_path):
            return bundle_path

    # 3. vendor/ directory (development / source installs)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    vendor_path = os.path.join(os.path.dirname(script_dir), 'vendor', executable_name)
    if os.path.exists(vendor_path):
        return vendor_path

    # 4. System PATH
    system_path = shutil.which(name)
    if system_path:
        return system_path

    raise FileNotFoundError(f"'{name}' not found. Please reinstall the downloader.")

def get_ytdlp_path():
    """Returns the absolute path to the yt-dlp executable."""
    return _find_executable('yt-dlp')

def get_ffmpeg_path():
    """Returns the absolute path to the ffmpeg executable."""
    return _find_executable('ffmpeg')


def update_ytdlp(progress_callback):
    """
    Cross-platform transparent Core Updater for the `yt-dlp` executable engine.
    Solves the '1-month bundle expiration' issue by dynamically overriding binary paths.
    """
    try:
        is_frozen = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        
        if is_frozen and platform.system() == 'Windows':
            import urllib.request
            appdata = os.environ.get('APPDATA', '') or os.path.expanduser('~')
            ext_dir = os.path.join(appdata, 'YouTubeNativeExt')
            os.makedirs(ext_dir, exist_ok=True)
            new_ytdlp_path = os.path.join(ext_dir, 'yt-dlp.exe')
            
            progress_callback({
                "type": "progress",
                "percent": "50%",
                "speed": "Downloading engine...",
                "eta": "00:05",
                "title": "yt-dlp Core Updater"
            })
            
            urllib.request.urlretrieve("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", new_ytdlp_path)
        else:
            # Mac/Linux Native Python distribution
            progress_callback({
                "type": "progress",
                "percent": "50%",
                "speed": "Upgrading via PIP...",
                "eta": "00:05",
                "title": "yt-dlp Core Updater"
            })
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], check=True)
            
        progress_callback({
            "type": "done",
            "filename": "yt-dlp Core Updater",
            "size_mb": 0,
            "title": "yt-dlp Core Updater"
        })
        log.info("[Downloader] yt-dlp Core Update Success.")
        return {"type": "done", "message": "Core updated successfully."}
        
    except Exception as e:
        log.error(f"[Updater] Failed to update yt-dlp: {e}")
        progress_callback({
            "type": "error",
            "message": f"Update failed: {e}",
            "title": "yt-dlp Core Updater"
        })
        return {"type": "error", "message": str(e)}

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
                    "max_height": int(v['itag']), # Semantically correct: this is a height boundary, not a real itag
                    "size_mb": v['size_mb']
                })
                
            if best_audio:
                qualities.append({
                    "label": "Audio Only (MP3)",
                    "max_height": "audio",
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
    # Add an explicit fallback ladder so yt-dlp doesn't throw "Requested format is not available"
    # if the exact resolution requested doesn't exist for the specific video.
    return (
        f"bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/"
        "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/"
        "bestvideo[height<=1080]+bestaudio/"
        "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/"
        "bestvideo[height<=720]+bestaudio/"
        "bestvideo+bestaudio/"
        "best/"
        "bestvideo/"
        "bestaudio"
    )

def download_video(url, max_height, output_dir, progress_callback, cookies_browser=None):
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
    
    # Process Cookie Injection disabled by default to prevent 10-second SQLite copy sweeps.
    cookie_dict = None
        
    # Analyze format to build selector sequence
    if max_height == "audio":
        cmd.extend([
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3"
        ])
    else:
        try:
            h = int(max_height)
        except (ValueError, TypeError):
            log.warning(f"[Downloader] Non-integer max_height '{max_height}' received — defaulting to 1080p.")
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
    
    # Ultra-permissive extraction logic to prevent UI process stalls
    # Matches: "[download]  14.5% of   20.10MiB at    3.45MiB/s ETA 00:04"
    # Even if "of", "at" or "ETA" is translated/missing, it forcefully grabs the %
    progress_regex = re.compile(r'\[download\][^\d]*([\d.]+)%')
    speed_regex = re.compile(r'at\s+([~]?[\d.]+[A-Za-z]+/s)')
    eta_regex = re.compile(r'ETA\s+([\d:]+)')
    
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
                
            if '[download]' in clean_line and '%' in clean_line:
                prog_match = progress_regex.search(clean_line)
                speed_match = speed_regex.search(clean_line)
                eta_match = eta_regex.search(clean_line)
                
                percent = f"{prog_match.group(1)}%" if prog_match else "Downloading..."
                speed = speed_match.group(1) if speed_match else ""
                eta = eta_match.group(1) if eta_match else ""
                
                progress_callback({
                    "type": "progress",
                    "percent": percent,
                    "speed": speed,
                    "eta": eta
                })
        
        process.stdout.close()
        process.wait()
        
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
