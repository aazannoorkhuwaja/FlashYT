import subprocess
import threading
import os
import re
import uuid
import json
import shutil
import time
import http.cookiejar
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
# Enable CORS for the Tampermonkey script
CORS(app)

# Global dictionary to store the status of downloads
# Key = job_id, Value = status dictionary
download_statuses = {}

# Pre-compile the ANSI escape code regex
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ============== CONFIG MANAGEMENT ==============

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULT_CONFIG = {
    "download_dir": os.path.expanduser("~/Downloads"),
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

    try:
        print(f"[Server] Extracting cookies from {browser} (one-time)...")
        # Use yt-dlp's own cookie extraction
        ydl_opts = {
            'cookiesfrombrowser': (browser,),
            'quiet': True,
            'skip_download': True,
        }
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

def get_cookie_opts():
    """
    Returns the yt-dlp cookie options.
    Uses cached cookie file if available (fast), otherwise falls back to live extraction (slow).
    """
    # Check if cookies need refreshing
    if time.time() - last_cookie_refresh > COOKIE_REFRESH_INTERVAL:
        with cookie_lock:
            if time.time() - last_cookie_refresh > COOKIE_REFRESH_INTERVAL:
                threading.Thread(target=extract_cookies_to_file, daemon=True).start()

    if os.path.exists(COOKIE_FILE):
        return {'cookiefile': COOKIE_FILE}
    
    # If the file hasn't been created yet (or failed), we DO NOT fall back to live extraction.
    # Live extraction breaks the download completely if the browser's cookie DB is missing or locked.
    return {}


# ============== DOWNLOAD LOGIC ==============

def run_download_thread(url, selected_format, job_id):
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
    }

    # Use cached cookies for speed (extracted once at startup)
    cookie_opts = get_cookie_opts()
    ydl_opts.update(cookie_opts)
    if cookie_opts:
        print(f"[Server] Using {'cached cookie file' if 'cookiefile' in cookie_opts else 'live browser cookies'}.")
    else:
        print("[Server] No cookies available. Proceeding without cookies.")

    if "MP4" in selected_format:
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
            ydl.download([url])

        # Fallback if hooks don't fire for the final step
        if download_statuses.get(job_id, {}).get("status") != "finished":
            download_statuses[job_id] = {
                "status": "finished",
                "percent": "100%",
                "speed": "-",
                "filename": ""
            }
    except Exception as e:
        download_statuses[job_id] = {
            "status": "error",
            "error": str(e)
        }


@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    selected_format = "MP4"

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

    thread = threading.Thread(target=run_download_thread, args=(url, selected_format, job_id))
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Download started in background", "job_id": job_id}), 202


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    status = download_statuses.get(job_id, {"status": "idle"})
    return jsonify(status), 200


@app.route('/config', methods=['GET'])
def get_config():
    """Return current configuration to the userscript settings panel."""
    return jsonify(app_config), 200


@app.route('/browse', methods=['GET'])
def browse_folders():
    """List subdirectories for the folder picker UI."""
    path = request.args.get('path', os.path.expanduser('~'))
    path = os.path.expanduser(path)

    if not os.path.isdir(path):
        return jsonify({"error": "Not a valid folder"}), 400

    try:
        folders = []
        for entry in sorted(os.scandir(path), key=lambda e: e.name.lower()):
            if entry.is_dir() and not entry.name.startswith('.'):
                folders.append(entry.name)

        parent = os.path.dirname(path)
        return jsonify({
            "current": path,
            "parent": parent if parent != path else None,
            "folders": folders
        }), 200
    except PermissionError:
        return jsonify({"error": "Cannot access this folder (permission denied)"}), 403


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
