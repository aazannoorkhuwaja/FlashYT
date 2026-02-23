import subprocess
import threading
import os
import re
import uuid
import json
import shutil
import time
import sys
import http.cookiejar
import tkinter as tk

def get_ffmpeg_path():
    """
    Returns the path to the ffmpeg executable.
    If running as a compiled PyInstaller executable, returns the bundled ffmpeg from _MEIPASS.
    Otherwise, assumes 'ffmpeg' is in the system PATH.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        import platform
        base_path = sys._MEIPASS
        if platform.system() == "Windows":
            return os.path.join(base_path, "ffmpeg.exe")
        return os.path.join(base_path, "ffmpeg")
    return shutil.which("ffmpeg") or "ffmpeg"
from tkinter import filedialog
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
# Enable CORS for the Tampermonkey script
CORS(app)

# Global dictionary to store the status of downloads
# Key = job_id, Value = status dictionary
download_statuses = {}
yt_info_cache = {} # Cache for fast download starts: {url: (timestamp, info_dict)}

# Pre-compile the ANSI escape code regex
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ============== CONFIG MANAGEMENT ==============

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULT_CONFIG = {
    "download_dir": "",
    "browser": "auto"
}

def load_config():
    """Load config from config.json, creating it with defaults if it doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
            # Merge with defaults so new keys are always present
            config = {**DEFAULT_CONFIG, **saved}
            return config
        except (json.JSONDecodeError, IOError):
            pass
    # First run or corrupt file — create fresh config
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def save_config(config):
    """Save config to config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load config at startup
app_config = load_config()

# ============== BROWSER AUTO-DETECTION ==============

# Priority order: most common browsers first
BROWSER_PRIORITY = ['brave', 'chrome', 'chromium', 'firefox', 'edge', 'opera']

# Linux binary names for each browser
BROWSER_EXECUTABLES = {
    'brave': ['brave-browser', 'brave'],
    'chrome': ['google-chrome', 'google-chrome-stable'],
    'chromium': ['chromium-browser', 'chromium'],
    'firefox': ['firefox'],
    'edge': ['microsoft-edge', 'microsoft-edge-stable'],
    'opera': ['opera'],
}

def detect_browser():
    """
    Auto-detect which browser is installed on the system.
    Returns the first browser found from the priority list, or None.
    """
    for browser in BROWSER_PRIORITY:
        executables = BROWSER_EXECUTABLES.get(browser, [browser])
        for exe in executables:
            if shutil.which(exe):
                print(f"[Server] Auto-detected browser: {browser}")
                return browser
    print("[Server] No supported browser detected for cookie import. Downloads will work but age-restricted videos may fail.")
    return None

def get_active_browser():
    """
    Get the browser to use for cookie import.
    Uses user's config choice, or auto-detects if set to 'auto'.
    """
    choice = app_config.get('browser', 'auto')
    if choice == 'auto':
        return detect_browser()
    elif choice == 'none':
        return None
    else:
        return choice


# ============== COOKIE CACHING (SPEED OPTIMIZATION) ==============

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cached_cookies.txt')
cookie_lock = threading.Lock()
last_cookie_refresh = 0
COOKIE_REFRESH_INTERVAL = 1800  # 30 minutes

import platform
import glob
import tempfile

def copy_browser_cookies(browser, target_dir):
    """
    Finds the browser's SQLite cookie database and copies it to a temporary
    directory structure that yt-dlp expects. This prevents "database is locked" errors.
    """
    system = platform.system()
    home = os.path.expanduser("~")
    
    paths = []
    if system == "Windows":
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        app_data = os.environ.get('APPDATA', '')
        if browser == 'chrome':
            paths.append(os.path.join(local_app_data, r"Google\Chrome\User Data\Default\Network\Cookies"))
        elif browser == 'brave':
            paths.append(os.path.join(local_app_data, r"BraveSoftware\Brave-Browser\User Data\Default\Network\Cookies"))
        elif browser == 'edge':
            paths.append(os.path.join(local_app_data, r"Microsoft\Edge\User Data\Default\Network\Cookies"))
        elif browser == 'opera':
            paths.append(os.path.join(app_data, r"Opera Software\Opera Stable\Network\Cookies"))
        elif browser == 'firefox':
            paths.extend(glob.glob(os.path.join(app_data, r"Mozilla\Firefox\Profiles\*\cookies.sqlite")))
    elif system == "Darwin":
        if browser == 'chrome':
            paths.append(os.path.join(home, "Library/Application Support/Google/Chrome/Default/Cookies"))
        elif browser == 'brave':
            paths.append(os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies"))
        elif browser == 'edge':
            paths.append(os.path.join(home, "Library/Application Support/Microsoft Edge/Default/Cookies"))
        elif browser == 'firefox':
            paths.extend(glob.glob(os.path.join(home, "Library/Application Support/Firefox/Profiles/*/cookies.sqlite")))
    else: # Linux
        if browser == 'chrome':
            paths.append(os.path.join(home, ".config/google-chrome/Default/Cookies"))
        elif browser == 'chromium':
            paths.append(os.path.join(home, ".config/chromium/Default/Cookies"))
        elif browser == 'brave':
            paths.append(os.path.join(home, ".config/BraveSoftware/Brave-Browser/Default/Cookies"))
        elif browser == 'edge':
            paths.append(os.path.join(home, ".config/microsoft-edge/Default/Cookies"))
        elif browser == 'firefox':
            paths.extend(glob.glob(os.path.join(home, ".mozilla/firefox/*/cookies.sqlite")))

    for db_path in paths:
        if os.path.exists(db_path):
            try:
                if browser == 'firefox':
                    shutil.copy2(db_path, os.path.join(target_dir, "cookies.sqlite"))
                else:
                    shutil.copy2(db_path, os.path.join(target_dir, "Cookies"))
                    network_dir = os.path.join(target_dir, "Network")
                    os.makedirs(network_dir, exist_ok=True)
                    shutil.copy2(db_path, os.path.join(network_dir, "Cookies"))
                return target_dir
            except Exception as e:
                print(f"[Server] Failed to copy cookie DB from {db_path}: {e}")
                
    return None

def extract_cookies_to_file():
    """
    Extract cookies from the browser ONCE and save to a Netscape cookie file.
    This avoids the 3-5 second decryption on every single download.
    """
    global last_cookie_refresh
    browser = get_active_browser()
    if not browser:
        print("[Server] No browser configured — skipping cookie extraction.")
        return False

    temp_dir = tempfile.mkdtemp()
    try:
        print(f"[Server] Extracting cookies from {browser} (one-time)...")
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }
        
        # Copy SQLite DB to avoid lock errors
        profile_dir = copy_browser_cookies(browser, temp_dir)
        if profile_dir:
            ydl_opts['cookiesfrombrowser'] = (browser, profile_dir)
            print(f"[Server] Copied SQLite cookie DB to temp file to prevent lock errors.")
        else:
            ydl_opts['cookiesfrombrowser'] = (browser,)
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # yt-dlp loads cookies into its cookie jar — we save them to a file
            cookie_jar = ydl.cookiejar
            if cookie_jar:
                cookie_jar.save(COOKIE_FILE, ignore_discard=True, ignore_expires=True)
                last_cookie_refresh = time.time()
                count = len(list(cookie_jar))
                print(f"[Server] ✓ Cached {count} cookies to file. Downloads will be instant now!")
                return True
            else:
                print("[Server] No cookies found in browser.")
                return False
    except Exception as e:
        print(f"[Server] Cookie extraction failed: {e}")
        print("[Server] Downloads will still work but may be slower.")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def get_cookie_opts():
    """
    Returns the yt-dlp cookie options.
    Uses cached cookie file if available (fast), otherwise falls back to live extraction (slow).
    """
    if os.path.exists(COOKIE_FILE):
        return {'cookiefile': COOKIE_FILE}
    
    # If the file hasn't been created yet (or failed), we DO NOT fall back to live extraction.
    # Live extraction breaks the download completely if the browser's cookie DB is missing or locked.
    return {}


# ============== DOWNLOAD LOGIC ==============

def run_download_thread(url, selected_format, job_id, cached_info=None):
    """
    Runs yt-dlp in a separate background thread.
    Hooks are defined inside to capture the job_id closure.
    """
    # Track how many streams have finished downloading (video=1, audio=2)
    stream_finish_count = {"count": 0, "expected": 2 if "MP4" in selected_format else 1}

    def update_progress(d):
        """Hook function called by yt_dlp during the download process."""
        if job_id not in download_statuses:
            return

        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%')
            speed_str = d.get('_speed_str', '0MiB/s')

            # Clean up ANSI escape codes
            percent_str = ansi_escape.sub('', percent_str).strip()
            speed_str = ansi_escape.sub('', speed_str).strip()

            download_statuses[job_id] = {
                "status": "downloading",
                "percent": percent_str,
                "speed": speed_str,
                "filename": os.path.basename(d.get('filename', ''))
            }
        elif d['status'] == 'finished':
            stream_finish_count["count"] += 1

            if stream_finish_count["count"] >= stream_finish_count["expected"]:
                # All streams downloaded, FFmpeg will merge
                download_statuses[job_id] = {
                    "status": "processing",
                    "percent": "100%",
                    "speed": "-",
                    "filename": os.path.basename(d.get('filename', ''))
                }
            else:
                download_statuses[job_id] = {
                    "status": "downloading",
                    "percent": "50%",
                    "speed": "fetching audio...",
                    "filename": os.path.basename(d.get('filename', ''))
                }
        elif d['status'] == 'error':
            download_statuses[job_id] = {
                "status": "error",
                "error": "yt-dlp encountered an error during download."
            }

    def postprocessor_hook(d):
        """Hook called by yt-dlp when a postprocessor starts/finishes."""
        if d['status'] == 'started':
            download_statuses[job_id] = {
                "status": "processing",
                "percent": "100%",
                "speed": "merging...",
                "filename": ""
            }
        elif d['status'] == 'finished':
            download_statuses[job_id] = {
                "status": "finished",
                "percent": "100%",
                "speed": "-",
                "filename": os.path.basename(d.get('filename', ''))
            }

    # Use download dir from live config
    download_dir = os.path.expanduser(app_config.get('download_dir', '~/Downloads'))
    outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'progress_hooks': [update_progress],
        'postprocessor_hooks': [postprocessor_hook],
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        
        # Allow yt-dlp to download the JS Challenge Solver
        'remote_components': ['ejs:github'],

        # Network Resilience & Retry Logic
        'retries': float('inf'),
        'fragment_retries': float('inf'),
        'file_access_retries': float('inf'),
        'retry_sleep_functions': {'http': lambda n: 5},
        'continuedl': True,
        
        # Speed: skip YouTube's mandatory 4-second throttle sleep
        'sleep_interval': 0,
        'sleep_interval_requests': 0,

        # Force TV client only — avoids the failing ios/android API calls
        # that waste 8+ seconds in retries. TV client returns ALL formats (144p-4K).
        'extractor_args': {'youtube': {'player_client': ['tv']}},

        # Bundled FFmpeg Support
        'ffmpeg_location': get_ffmpeg_path(),
    }

    # Use cached cookies for speed (extracted once at startup)
    cookie_opts = get_cookie_opts()
    ydl_opts.update(cookie_opts)
    if cookie_opts:
        print(f"[Server] Using {'cached cookie file' if 'cookiefile' in cookie_opts else 'live browser cookies'}.")
    else:
        print("[Server] No cookies available. Proceeding without cookies.")

    if selected_format and selected_format not in ["MP4", "MP3"]:
        ydl_opts['format'] = selected_format
        ydl_opts['merge_output_format'] = 'mp4'
    elif "MP4" in selected_format:
        # Safest fallback chain to avoid "Requested format is not available" errors:
        # 1. Best mp4 video <= 1080p + best m4a audio
        # 2. Best video <= 1080p + best audio (any formats)
        # 3. Best video + best audio (any resolution)
        # 4. Best pre-merged format (usually 720p/360p)
        # 5. Best video only (silent video fallback)
        # 6. Best audio only (audio-only fallback)
        ydl_opts['format'] = (
            'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/'
            'bestvideo[height<=1080]+bestaudio/'
            'bestvideo+bestaudio/'
            'best/'
            'bestvideo/'
            'bestaudio'
        )
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitleslangs'] = ['en', 'all']
        ydl_opts['embedsubtitles'] = True
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegEmbedSubtitle'
        }]
    elif "MP3" in selected_format:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if cached_info:
                try:
                    print(f"[Server] Attempting instant 1-second download from cache...")
                    ydl.process_ie_result(cached_info, download=True)
                except Exception as e:
                    print(f"[Server] Cache failed ({e}). Falling back to fresh extraction...")
                    ydl.download([url])
            else:
                ydl.download([url])
    except Exception as first_error:
        # If the specific format ID failed, retry with a safe generic format
        error_str = str(first_error).lower()
        if 'format' in error_str or 'not available' in error_str or 'requested' in error_str:
            print(f"[Server] Format '{ydl_opts.get('format')}' failed. Retrying with generic format...")
            ydl_opts['format'] = (
                'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/'
                'bestvideo[height<=1080]+bestaudio/'
                'bestvideo+bestaudio/'
                'best/'
                'bestvideo/'
                'bestaudio'
            )
            ydl_opts['merge_output_format'] = 'mp4'
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])
            except Exception as retry_error:
                download_statuses[job_id] = {
                    "status": "error",
                    "error": str(retry_error)
                }
                return
        else:
            download_statuses[job_id] = {
                "status": "error",
                "error": str(first_error)
            }
            return

    # Fallback if hooks don't fire for the final step
    if download_statuses.get(job_id, {}).get("status") != "finished":
        download_statuses[job_id] = {
            "status": "finished",
            "percent": "100%",
            "speed": "-",
            "filename": ""
        }


@app.route('/get_formats', methods=['POST'])
def get_formats():
    """Fetch available qualities and estimated sizes."""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Strip playlist parameters from URL so yt-dlp only fetches the single video
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    clean_params = {k: v for k, v in params.items() if k in ('v',)}
    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
    url = urllib.parse.urlunparse(parsed._replace(query=clean_query))

    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        # Force TV client only — avoids the failing ios/android API calls
        'extractor_args': {'youtube': {'player_client': ['tv']}},
    }

    # Add optional cookies
    cookie_opts = get_cookie_opts()
    if cookie_opts:
        ydl_opts.update(cookie_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            yt_info_cache[url] = (time.time(), info) # Cache info with timestamp
            formats_data = info.get('formats', [])
            duration = info.get('duration', 0)
            
            # Find best audio for combination
            audio_formats = [f for f in formats_data if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0) if audio_formats else None
            
            audio_filesize = 0
            if best_audio:
                audio_filesize = best_audio.get('filesize') or best_audio.get('filesize_approx')
                if not audio_filesize:
                    abr = best_audio.get('abr') or best_audio.get('tbr') or 128
                    audio_filesize = int(abr * 1024 * duration / 8)
                audio_filesize = audio_filesize or 0
            
            # Find best video for each resolution
            video_resolutions = {}
            for f in formats_data:
                height = f.get('height')
                if not height or f.get('vcodec') == 'none':
                    continue
                
                v_filesize = f.get('filesize') or f.get('filesize_approx')
                if not v_filesize:
                    vbr = f.get('vbr') or f.get('tbr')
                    if not vbr:
                        # Fallback rough estimates based on typical YouTube bitrates (Kbps)
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
                    elif ext == old['ext'] and (v_filesize + audio_filesize) > old['size_bytes']:
                        is_better = True
                
                if is_better:
                    video_resolutions[height] = {
                        'format_id': f"{f.get('format_id')}+{best_audio.get('format_id')}" if best_audio else f.get('format_id'),
                        'resolution': f"{height}p",
                        'height': height,
                        'ext': ext,
                        'size_bytes': v_filesize + audio_filesize,
                        'fps': f.get('fps', 30)
                    }
                    
            sorted_vids = sorted(video_resolutions.values(), key=lambda x: x['height'], reverse=True)
            
            return jsonify({
                "status": "success",
                "title": info.get('title'),
                "formats": sorted_vids,
                "audio_only": {
                    "format_id": best_audio.get('format_id') if best_audio else "bestaudio",
                    "ext": best_audio.get('ext') if best_audio else "m4a",
                    "size_bytes": audio_filesize
                } if best_audio else None
            }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    selected_format = data.get('format', 'MP4')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Strip playlist parameters from URL so yt-dlp only downloads the single video
    # YouTube URLs like watch?v=xxx&list=yyy cause yt-dlp to download the entire playlist
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    # Keep only the video ID parameter, strip list/index/start_radio etc.
    clean_params = {k: v for k, v in params.items() if k in ('v',)}
    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
    url = urllib.parse.urlunparse(parsed._replace(query=clean_query))
    print(f"[Server] Sanitized URL: {url}")
    
    # Generate unique ID for this download
    job_id = str(uuid.uuid4())

    # Initialize the status
    download_statuses[job_id] = {
        "status": "starting",
        "percent": "0%",
        "speed": "0MiB/s"
    }

    # Ensure download directory exists
    download_dir = os.path.expanduser(app_config.get('download_dir', '~/Downloads'))
    os.makedirs(download_dir, exist_ok=True)

    # Fetch cached info if it exists and is less than 15 minutes old
    cached_info = None
    if url in yt_info_cache:
        timestamp, info = yt_info_cache[url]
        if time.time() - timestamp < 900: # 15 minutes
            cached_info = info
        else:
            del yt_info_cache[url]

    thread = threading.Thread(target=run_download_thread, args=(url, selected_format, job_id, cached_info))
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Download started in background", "job_id": job_id}), 202


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    status = download_statuses.get(job_id, {"status": "idle"})
    return jsonify(status), 200

@app.route('/progress', methods=['GET'])
def get_all_progress():
    """Returns all active download statuses for the global dashboard."""
    # Filter out idle/error/finished jobs older than a certain time if we wanted to
    # For now, return all of them
    return jsonify(download_statuses), 200


@app.route('/config', methods=['GET'])
def get_config():
    """Return current configuration to the userscript settings panel."""
    return jsonify(app_config), 200

@app.route('/choose_folder', methods=['POST'])
def choose_folder():
    """Opens a native OS folder selection dialog."""
    try:
        # Hide the main tkinter window
        root = tk.Tk()
        root.withdraw()
        # Bring the dialog to the front
        root.attributes('-topmost', True)
        
        # Open the folder selection dialog
        folder_path = filedialog.askdirectory(
            title="Select Download Folder for One-Click YouTube Downloader"
        )
        root.destroy()
        
        if folder_path:
            app_config['download_dir'] = folder_path
            save_config(app_config)
            return jsonify({"status": "success", "path": folder_path}), 200
        else:
            return jsonify({"status": "cancelled"}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration from the userscript settings panel."""
    global app_config
    data = request.json

    if 'download_dir' in data:
        path = os.path.expanduser(data['download_dir'])
        # Validate the path is a writeable directory (or can be created)
        try:
            os.makedirs(path, exist_ok=True)
            app_config['download_dir'] = data['download_dir']
        except OSError as e:
            return jsonify({"error": f"Cannot use that folder: {str(e)}"}), 400

    if 'browser' in data:
        allowed = ['auto', 'none'] + BROWSER_PRIORITY
        if data['browser'] in allowed:
            app_config['browser'] = data['browser']
        else:
            return jsonify({"error": f"Browser must be one of: {', '.join(allowed)}"}), 400

    save_config(app_config)

    # Re-extract cookies if browser was changed
    if 'browser' in data:
        threading.Thread(target=extract_cookies_to_file, daemon=True).start()

    return jsonify({"message": "Settings saved!", "config": app_config}), 200


@app.route('/refresh-cookies', methods=['POST'])
def refresh_cookies():
    """Manually trigger a cookie re-extraction (if user logged into YouTube)."""
    success = extract_cookies_to_file()
    if success:
        return jsonify({"message": "Cookies refreshed!"}), 200
    else:
        return jsonify({"error": "Could not extract cookies. Check server logs."}), 500


if __name__ == '__main__':
    # On Windows with a bundled .exe, auto-register for startup on boot
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        import platform
        try:
            exe_path = sys.executable
            startup_dir = os.path.join(os.environ.get('APPDATA', ''), 
                                        'Microsoft', 'Windows', 'Start Menu', 
                                        'Programs', 'Startup')
            vbs_path = os.path.join(startup_dir, 'YouTubeDownloader.vbs')
            if not os.path.exists(vbs_path):
                # Create a VBS script that launches the .exe silently (no terminal window)
                vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\n'
                vbs_content += f'WshShell.Run Chr(34) & "{exe_path}" & Chr(34), 0, False\n'
                with open(vbs_path, 'w') as f:
                    f.write(vbs_content)
                print(f"[Server] ✓ Auto-start configured! This app will now launch silently on every boot.")
            else:
                print(f"[Server] ✓ Auto-start already configured.")
        except Exception as e:
            print(f"[Server] Could not set up auto-start: {e}")

    print(f"[Server] Download folder: {os.path.expanduser(app_config.get('download_dir', '~/Downloads'))}")
    print(f"[Server] Browser for cookies: {app_config.get('browser', 'auto')}")
    browser_name = get_active_browser()
    if browser_name:
        print(f"[Server] Detected browser: {browser_name}")
    else:
        print("[Server] No browser detected — cookies disabled")

    # Pre-extract cookies at startup so first download is instant
    extract_cookies_to_file()

    app.run(host='127.0.0.1', port=5000, debug=False)

