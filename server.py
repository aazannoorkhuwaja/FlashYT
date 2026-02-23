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
import stat
import urllib.request
import webbrowser
from datetime import datetime

# tkinter is optional — only needed for the folder picker dialog.
# It may not be available on headless servers or minimal Docker containers.
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# pystray + Pillow are used for the system tray icon.
# If they are missing, we fail fast with a clear error so the user knows what to install.
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY_DEPS = True
except ImportError:
    HAS_TRAY_DEPS = False

def get_ffmpeg_path():
    """
    Returns the path to the ffmpeg executable.
    Checks: PyInstaller bundle → project directory → system PATH.
    """
    # 1. Check if running as a compiled PyInstaller executable
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        import platform
        base_path = sys._MEIPASS
        if platform.system() == "Windows":
            return os.path.join(base_path, "ffmpeg.exe")
        return os.path.join(base_path, "ffmpeg")
    
    # 2. Check if ffmpeg.exe is in the same directory as server.py (portable install)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffmpeg = os.path.join(script_dir, 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    # 3. Check system PATH
    return shutil.which("ffmpeg") or "ffmpeg"

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yt_dlp

from werkzeug.serving import make_server

app = Flask(__name__)
# Enable CORS for the Tampermonkey script
CORS(app)

# Global dictionary to store the status of downloads
# Key = job_id, Value = status dictionary
download_statuses = {}
download_status_lock = threading.Lock()
yt_info_cache = {} # Cache for fast download starts: {url: (timestamp, info_dict)}

# Pre-compile the ANSI escape code regex
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ============== CONFIG MANAGEMENT ==============

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULT_CONFIG = {
    "download_dir": "",
    "browser": "auto"
}

def get_default_download_dir():
    """Returns a sensible default download directory for any platform."""
    if sys.platform == 'win32':
        # Windows: use the user's Downloads folder
        return os.path.join(os.path.expanduser('~'), 'Downloads')
    return os.path.expanduser('~/Downloads')

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

# ============== SIMPLE TRAY-FRIENDLY SERVER WRAPPER ==============

# Paths used for yt-dlp standalone binary auto-updates
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
YT_DLP_BINARY_PATH = os.path.join(
    SCRIPT_DIR,
    'yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp'
)
YT_DLP_VERSION_FILE = os.path.join(SCRIPT_DIR, '.yt_dlp_version.json')


class FlaskServerThread(threading.Thread):
    """
    Runs the Flask app on a background thread using werkzeug's make_server.
    This gives us a simple way to start/stop the HTTP server from the tray.
    """

    def __init__(self, flask_app, host='127.0.0.1', port=5000):
        super().__init__(daemon=True)
        self.flask_app = flask_app
        self.host = host
        self.port = port
        self._server = None

    def run(self):
        # We create the WSGI server here so it lives for the thread's lifetime.
        self._server = make_server(self.host, self.port, self.flask_app)
        self._server.serve_forever()

    def shutdown(self):
        # Called from the tray when the user clicks Quit.
        if self._server is not None:
            self._server.shutdown()


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
cookie_ready = threading.Event()  # Signals when initial cookie extraction is done
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
    try:
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
                # End users can have a global yt-dlp config that forces a bad format (-f ...).
                # We ignore all external configs so behavior is consistent across machines.
                'ignoreconfig': True,
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
    finally:
        # ALWAYS signal that cookie extraction is done (success or failure)
        # so get_cookie_opts() never blocks forever
        cookie_ready.set()


# ============== yt-dlp STANDALONE BINARY AUTO-UPDATER ==============


def _read_local_yt_dlp_version():
    """
    Reads the last downloaded yt-dlp release tag from a small JSON file.
    This lets us avoid re-downloading the same version every startup.
    """
    if not os.path.exists(YT_DLP_VERSION_FILE):
        return None
    try:
        with open(YT_DLP_VERSION_FILE, 'r') as f:
            data = json.load(f)
        return data.get('tag')
    except Exception:
        return None


def _write_local_yt_dlp_version(tag):
    """Persists the current yt-dlp tag to disk so we can compare next time."""
    try:
        with open(YT_DLP_VERSION_FILE, 'w') as f:
            json.dump({'tag': tag}, f)
    except Exception as e:
        print(f"[Updater] Failed to write yt-dlp version file: {e}")


def download_latest_yt_dlp_binary():
    """
    Background helper that checks GitHub for the latest yt-dlp release and,
    if a newer version is available, downloads the standalone binary next to server.py.

    We keep this logic simple and defensive:
    - If GitHub is unreachable, we log and silently skip.
    - If anything fails mid-way, we do not touch the existing binary.
    """
    api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
    print("[Updater] Checking for yt-dlp updates...")

    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.status != 200:
                print(f"[Updater] GitHub API returned status {resp.status}. Skipping update.")
                return
            release = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[Updater] Could not query GitHub for yt-dlp: {e}")
        return

    latest_tag = release.get('tag_name')
    if not latest_tag:
        print("[Updater] Could not determine latest yt-dlp tag. Skipping.")
        return

    current_tag = _read_local_yt_dlp_version()
    if current_tag == latest_tag and os.path.exists(YT_DLP_BINARY_PATH):
        print(f"[Updater] yt-dlp is already up to date ({latest_tag}).")
        return

    # Decide which asset to download based on platform.
    wanted_name = 'yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp'
    assets = release.get('assets') or []
    download_url = None
    for asset in assets:
        if asset.get('name') == wanted_name:
            download_url = asset.get('browser_download_url')
            break

    if not download_url:
        print(f"[Updater] Could not find asset {wanted_name} in latest release. Skipping.")
        return

    print(f"[Updater] Downloading {wanted_name} ({latest_tag})...")
    tmp_path = YT_DLP_BINARY_PATH + ".tmp"

    try:
        with urllib.request.urlopen(download_url, timeout=60) as resp, open(tmp_path, 'wb') as out_f:
            shutil.copyfileobj(resp, out_f)

        # Make the file executable on Unix-like systems.
        if sys.platform != 'win32':
            st = os.stat(tmp_path)
            os.chmod(tmp_path, st.st_mode | stat.S_IEXEC)

        # Replace the old binary atomically.
        os.replace(tmp_path, YT_DLP_BINARY_PATH)
        _write_local_yt_dlp_version(latest_tag)
        print(f"[Updater] yt-dlp updated to {latest_tag} at {YT_DLP_BINARY_PATH}")
    except Exception as e:
        # Clean up the partially downloaded file if something goes wrong.
        print(f"[Updater] Failed to update yt-dlp: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


# ============== yt-dlp STANDALONE BINARY AUTO-UPDATER ==============


def _read_local_yt_dlp_version():
    """
    Reads the last downloaded yt-dlp release tag from a small JSON file.
    This lets us avoid re-downloading the same version every startup.
    """
    if not os.path.exists(YT_DLP_VERSION_FILE):
        return None
    try:
        with open(YT_DLP_VERSION_FILE, 'r') as f:
            data = json.load(f)
        return data.get('tag')
    except Exception:
        return None


def _write_local_yt_dlp_version(tag):
    """Persists the current yt-dlp tag to disk so we can compare next time."""
    try:
        with open(YT_DLP_VERSION_FILE, 'w') as f:
            json.dump({'tag': tag}, f)
    except Exception as e:
        print(f"[Updater] Failed to write yt-dlp version file: {e}")


def download_latest_yt_dlp_binary():
    """
    Background helper that checks GitHub for the latest yt-dlp release and,
    if a newer version is available, downloads the standalone binary next to server.py.

    We keep this logic simple and defensive:
    - If GitHub is unreachable, we log and silently skip.
    - If anything fails mid-way, we do not touch the existing binary.
    """
    api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
    print("[Updater] Checking for yt-dlp updates...")

    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.status != 200:
                print(f"[Updater] GitHub API returned status {resp.status}. Skipping update.")
                return
            release = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[Updater] Could not query GitHub for yt-dlp: {e}")
        return

    latest_tag = release.get('tag_name')
    if not latest_tag:
        print("[Updater] Could not determine latest yt-dlp tag. Skipping.")
        return

    current_tag = _read_local_yt_dlp_version()
    if current_tag == latest_tag and os.path.exists(YT_DLP_BINARY_PATH):
        print(f"[Updater] yt-dlp is already up to date ({latest_tag}).")
        return

    # Decide which asset to download based on platform.
    wanted_name = 'yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp'
    assets = release.get('assets') or []
    download_url = None
    for asset in assets:
        if asset.get('name') == wanted_name:
            download_url = asset.get('browser_download_url')
            break

    if not download_url:
        print(f"[Updater] Could not find asset {wanted_name} in latest release. Skipping.")
        return

    print(f"[Updater] Downloading {wanted_name} ({latest_tag})...")
    tmp_path = YT_DLP_BINARY_PATH + ".tmp"

    try:
        with urllib.request.urlopen(download_url, timeout=60) as resp, open(tmp_path, 'wb') as out_f:
            shutil.copyfileobj(resp, out_f)

        # Make the file executable on Unix-like systems.
        if sys.platform != 'win32':
            st = os.stat(tmp_path)
            os.chmod(tmp_path, st.st_mode | stat.S_IEXEC)

        # Replace the old binary atomically.
        os.replace(tmp_path, YT_DLP_BINARY_PATH)
        _write_local_yt_dlp_version(latest_tag)
        print(f"[Updater] yt-dlp updated to {latest_tag} at {YT_DLP_BINARY_PATH}")
    except Exception as e:
        # Clean up the partially downloaded file if something goes wrong.
        print(f"[Updater] Failed to update yt-dlp: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def get_cookie_opts():
    """
    Returns the yt-dlp cookie options.
    On first call, waits up to 15 seconds for background cookie extraction to finish.
    """
    # Wait for the initial cookie extraction to complete (max 15 seconds)
    if not cookie_ready.is_set():
        print("[Server] Waiting for cookie extraction to finish...")
        cookie_ready.wait(timeout=15)
    
    if os.path.exists(COOKIE_FILE):
        return {'cookiefile': COOKIE_FILE}
    
    return {}


# ============== DOWNLOAD LOGIC ==============

def run_download_thread(url, selected_format, job_id, cached_info=None):
    """
    Runs yt-dlp in a separate background thread.
    Hooks are defined inside to capture the job_id closure.
    """
    # Track how many streams have finished downloading (video=1, audio=2)
    stream_finish_count = {"count": 0, "expected": 2 if "MP4" in selected_format else 1}

    def set_status(job_id, payload):
        """
        Small helper so all status writes go through one place.
        This keeps things thread-safe when many downloads run in parallel.
        """
        with download_status_lock:
            current = download_statuses.get(job_id, {})
            current.update(payload)
            download_statuses[job_id] = current

    def update_progress(d):
        """Hook function called by yt_dlp during the download process."""
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%')
            speed_str = d.get('_speed_str', '0MiB/s')
            eta_str = d.get('_eta_str', '')

            # Clean up ANSI escape codes
            percent_str = ansi_escape.sub('', percent_str).strip()
            speed_str = ansi_escape.sub('', speed_str).strip()
            eta_str = ansi_escape.sub('', eta_str).strip()

            set_status(job_id, {
                "status": "downloading",
                "percent": percent_str,
                "speed": speed_str,
                "eta": eta_str,
                "filename": os.path.basename(d.get('filename', ''))
            })
        elif d['status'] == 'finished':
            stream_finish_count["count"] += 1

            if stream_finish_count["count"] >= stream_finish_count["expected"]:
                # All streams downloaded, FFmpeg will merge
                set_status(job_id, {
                    "status": "processing",
                    "percent": "100%",
                    "speed": "-",
                    "filename": os.path.basename(d.get('filename', ''))
                })
            else:
                set_status(job_id, {
                    "status": "downloading",
                    "percent": "50%",
                    "speed": "fetching audio...",
                    "filename": os.path.basename(d.get('filename', ''))
                })
        elif d['status'] == 'error':
            set_status(job_id, {
                "status": "error",
                "error": "yt-dlp encountered an error during download.",
                "error_at": time.time(),
            })

    def postprocessor_hook(d):
        """Hook called by yt-dlp when a postprocessor starts/finishes."""
        if d['status'] == 'started':
            set_status(job_id, {
                "status": "processing",
                "percent": "100%",
                "speed": "merging...",
                "filename": ""
            })
        elif d['status'] == 'finished':
            set_status(job_id, {
                "status": "finished",
                "percent": "100%",
                "speed": "-",
                "filename": os.path.basename(d.get('filename', '')),
                "finished_at": time.time(),
            })

    # Use download dir from live config
    download_dir = app_config.get('download_dir', '') or get_default_download_dir()
    download_dir = os.path.expanduser(download_dir)
    outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'progress_hooks': [update_progress],
        'postprocessor_hooks': [postprocessor_hook],
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        # Do not allow any global yt-dlp config to affect downloads.
        'ignoreconfig': True,

        # Network Resilience & Retry Logic
        'retries': float('inf'),
        'fragment_retries': float('inf'),
        'file_access_retries': float('inf'),
        'retry_sleep_functions': {'http': lambda n: 5},
        'continuedl': True,
        
        # Speed: skip YouTube's mandatory 4-second throttle sleep
        'sleep_interval': 0,
        'sleep_interval_requests': 0,

        # Anti-Bot Evasion: Impersonate a real browser requesting the web client
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },

        # Let yt-dlp choose the best client automatically.
        # DO NOT force 'tv' — YouTube now applies DRM to all TV client formats.
        # See: https://github.com/yt-dlp/yt-dlp/issues/12563

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

    def build_video_format_string(max_height):
        """
        Builds a safe yt-dlp format selector for the requested max height.
        We never rely on a single fragile itag, so users do not hit
        "requested format is not available" errors on edge videos.
        """
        try:
            h = int(max_height)
        except (TypeError, ValueError):
            h = 1080

        # Chain is ordered from most to least ideal.
        return (
            f"bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}]+bestaudio/"
            f"best[height<={h}]/"
            "bestvideo+bestaudio/"
            "best/"
            "bestvideo/"
            "bestaudio"
        )

    # Interpret the selection key coming from the userscript.
    # Examples:
    # - "video_1080"  → MP4 video up to 1080p with robust fallbacks
    # - "audio_only"  → best audio-only track (MP3/M4A)
    # - "MP4"/"MP3"   → legacy values kept for safety
    if isinstance(selected_format, str) and selected_format.startswith("video_"):
        try:
            requested_height = int(selected_format.split("_", 1)[1])
        except (IndexError, ValueError):
            requested_height = 1080
        ydl_opts['format'] = build_video_format_string(requested_height)
        ydl_opts['merge_output_format'] = 'mp4'
    elif selected_format == "audio_only" or "MP3" in str(selected_format):
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    elif "MP4" in str(selected_format):
        # Safest fallback chain to avoid "Requested format is not available" errors:
        # 1. Best mp4 video <= 1080p + best m4a audio
        # 2. Best video <= 1080p + best audio (any formats)
        # 3. Best video + best audio (any resolution)
        # 4. Best pre-merged format (usually 720p/360p)
        # 5. Best video only (silent video fallback)
        # 6. Best audio only (audio-only fallback)
        ydl_opts['format'] = build_video_format_string(1080)
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitleslangs'] = ['en', 'all']
        ydl_opts['embedsubtitles'] = True
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegEmbedSubtitle'
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
        # If the specific format selection failed, make one last attempt using
        # yt-dlp's own default "best" logic with *no* custom -f filter at all.
        error_str = str(first_error).lower()
        if 'requested format is not available' in error_str or 'use --list-formats' in error_str:
            print(f"[Server] Format '{ydl_opts.get('format')}' failed with "
                  f"'{first_error}'. Retrying once without any custom format selector...")
            # Remove any explicit format / merge hints and let yt-dlp decide.
            ydl_opts.pop('format', None)
            ydl_opts.pop('merge_output_format', None)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])
            except Exception as retry_error:
                set_status(job_id, {
                    "status": "error",
                    "error": str(retry_error),
                    "error_at": time.time(),
                })
                return
        else:
            # Non-format-related error, just surface it.
            set_status(job_id, {
                "status": "error",
                "error": str(first_error),
                "error_at": time.time(),
            })
            return

    # Fallback if hooks don't fire for the final step
    with download_status_lock:
        status = download_statuses.get(job_id, {})
    if status.get("status") != "finished":
        set_status(job_id, {
            "status": "finished",
            "percent": "100%",
            "speed": "-",
            "filename": status.get("filename", ""),
            "finished_at": time.time(),
        })


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
        'socket_timeout': 30,
        # CRITICAL: ignore user/global yt-dlp config files (often contain -f ...).
        # If we don't, /get_formats can fail on some machines with:
        # "Requested format is not available. Use --list-formats..."
        'ignoreconfig': True,

        # Network Resilience & Retry Logic
        'retries': float('inf'),
        'fragment_retries': float('inf'),
        'file_access_retries': float('inf'),
        'retry_sleep_functions': {'http': lambda n: 5},
        
        # Anti-Bot Evasion (matches download config)
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
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
                        'format_id': f"video_{height}",
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
                    "format_id": "audio_only",
                    "ext": "mp3",
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
    with download_status_lock:
        download_statuses[job_id] = {
            "status": "starting",
            "percent": "0%",
            "speed": "0MiB/s",
            "eta": "",
        }

    # Ensure download directory exists
    download_dir = app_config.get('download_dir', '') or get_default_download_dir()
    download_dir = os.path.expanduser(download_dir)
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
    # In practice the dashboard filters what it shows by finished/error timestamps
    # on the client side. Here we simply snapshot the current dict.
    with download_status_lock:
        snapshot = dict(download_statuses)
    return jsonify(snapshot), 200


@app.route('/config', methods=['GET'])
def get_config():
    """Return current configuration to the userscript settings panel."""
    return jsonify(app_config), 200

@app.route('/choose_folder', methods=['POST'])
def choose_folder():
    """Opens a native OS folder selection dialog."""
    if not HAS_TKINTER:
        # On headless/minimal systems, use the default Downloads folder
        default_dir = get_default_download_dir()
        os.makedirs(default_dir, exist_ok=True)
        app_config['download_dir'] = default_dir
        save_config(app_config)
        return jsonify({"status": "success", "path": default_dir}), 200
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


@app.route('/settings', methods=['GET'])
def settings_page():
    """
    Very small HTML settings UI.
    This is intentionally simple so non-technical users can change
    the download folder and browser choice without touching files.
    """
    # We inline the HTML here to keep things self-contained.
    # For a larger app, using templates would be better.
    allowed_browsers = ['auto', 'none'] + BROWSER_PRIORITY
    # Escape values minimally since these are controlled options.
    current_dir = app_config.get('download_dir', '') or get_default_download_dir()
    current_browser = app_config.get('browser', 'auto')

    options_html = "".join(
        f'<option value="{b}"{" selected" if b == current_browser else ""}>{b}</option>'
        for b in allowed_browsers
    )

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>One-Click YouTube Downloader – Settings</title>
  <style>
    body {{
      background: #121212;
      color: #ffffff;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 24px;
    }}
    .card {{
      max-width: 640px;
      margin: 0 auto;
      padding: 24px 28px;
      background: #1e1e1e;
      border-radius: 16px;
      border: 1px solid #333;
      box-shadow: 0 10px 30px rgba(0,0,0,0.7);
    }}
    h1 {{
      margin-top: 0;
      font-size: 22px;
    }}
    label {{
      display: block;
      font-size: 13px;
      color: #aaa;
      margin-bottom: 4px;
    }}
    input[type="text"], select {{
      width: 100%;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid #444;
      background: #181818;
      color: #fff;
      font-size: 14px;
      box-sizing: border-box;
    }}
    .row {{
      margin-bottom: 16px;
    }}
    button {{
      cursor: pointer;
      border-radius: 999px;
      border: none;
      padding: 8px 16px;
      font-size: 14px;
    }}
    .primary {{
      background: #cc0000;
      color: #fff;
      margin-right: 8px;
    }}
    .secondary {{
      background: #333;
      color: #eee;
    }}
    .status {{
      font-size: 13px;
      color: #8bc34a;
      margin-top: 8px;
      min-height: 18px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>One-Click YouTube Downloader – Settings</h1>

    <div class="row">
      <label for="download_dir">Download folder</label>
      <input id="download_dir" type="text" value="{current_dir}">
      <div style="margin-top: 8px;">
        <button class="secondary" id="choose_folder_btn">Choose with dialog…</button>
      </div>
    </div>

    <div class="row">
      <label for="browser">Browser for cookies (age-restricted videos)</label>
      <select id="browser">
        {options_html}
      </select>
    </div>

    <div class="row">
      <button class="primary" id="save_btn">Save</button>
      <button class="secondary" id="refresh_cookies_btn">Refresh cookies now</button>
      <div class="status" id="status_msg"></div>
    </div>
  </div>

  <script>
    const statusEl = document.getElementById('status_msg');

    function setStatus(msg, isError) {{
      statusEl.textContent = msg || '';
      statusEl.style.color = isError ? '#f44336' : '#8bc34a';
    }}

    document.getElementById('choose_folder_btn').onclick = function () {{
      setStatus('Opening folder picker…', false);
      fetch('/choose_folder', {{ method: 'POST' }})
        .then(r => r.json())
        .then(j => {{
          if (j.status === 'success') {{
            document.getElementById('download_dir').value = j.path;
            setStatus('Folder updated.', false);
          }} else if (j.status === 'cancelled') {{
            setStatus('Cancelled.', true);
          }} else {{
            setStatus(j.error || 'Failed to choose folder.', true);
          }}
        }})
        .catch(err => setStatus('Error: ' + err, true));
    }};

    document.getElementById('save_btn').onclick = function () {{
      const payload = {{
        download_dir: document.getElementById('download_dir').value,
        browser: document.getElementById('browser').value
      }};
      setStatus('Saving…', false);
      fetch('/config', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }})
        .then(r => r.json().then(j => [r.status, j]))
        .then(([status, j]) => {{
          if (status === 200) {{
            setStatus('Settings saved.', false);
          }} else {{
            setStatus(j.error || 'Failed to save settings.', true);
          }}
        }})
        .catch(err => setStatus('Error: ' + err, true));
    }};

    document.getElementById('refresh_cookies_btn').onclick = function () {{
      setStatus('Refreshing cookies…', false);
      fetch('/refresh-cookies', {{ method: 'POST' }})
        .then(r => r.json().then(j => [r.status, j]))
        .then(([status, j]) => {{
          if (status === 200) {{
            setStatus(j.message || 'Cookies refreshed.', false);
          }} else {{
            setStatus(j.error || 'Failed to refresh cookies.', true);
          }}
        }})
        .catch(err => setStatus('Error: ' + err, true));
    }};
  </script>
</body>
</html>
"""
    return html


def open_config_folder():
    """
    Opens the folder that contains config.json in the native file manager.
    This lets non-technical users find logs/config without touching the CLI.
    """
    folder = os.path.dirname(CONFIG_FILE)
    os.makedirs(folder, exist_ok=True)

    try:
        if sys.platform == 'win32':
            # Use explorer on Windows
            subprocess.Popen(['explorer', folder])
        elif sys.platform == 'darwin':
            # Use open on macOS
            subprocess.Popen(['open', folder])
        else:
            # Use xdg-open on Linux / other Unix
            subprocess.Popen(['xdg-open', folder])
    except Exception as e:
        print(f"[Server] Failed to open config folder: {e}")


def create_tray_image():
    """
    Creates a simple in-memory tray icon image.
    Keeping it generated avoids dealing with external asset files.
    """
    size = 64
    image = Image.new('RGBA', (size, size), (30, 30, 30, 255))
    draw = ImageDraw.Draw(image)

    # Draw a red rounded rectangle background
    margin = 8
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=12,
        fill=(204, 0, 0, 255)
    )

    # Draw a white "play" triangle in the center
    triangle = [
        (size * 0.40, size * 0.32),
        (size * 0.40, size * 0.68),
        (size * 0.70, size * 0.50),
    ]
    draw.polygon(triangle, fill=(255, 255, 255, 255))

    return image


def run_tray(server_thread):
    """
    Starts the system tray icon on the main thread and blocks until the user quits.
    The Flask server runs in server_thread in the background.
    """
    if not HAS_TRAY_DEPS:
        # We keep this simple: fail loudly so the user knows what to install.
        print("[Server] pystray and Pillow are required for the system tray.")
        print("[Server] Install them with: pip install pystray pillow")
        # If there is no tray, at least keep the process alive with the server running.
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server_thread.shutdown()
            return

    def on_quit(icon, item):
        # User chose Quit from the tray menu: stop HTTP server then tray icon.
        print("[Tray] Quit selected. Shutting down server...")
        server_thread.shutdown()
        icon.visible = False
        icon.stop()

    def on_open_settings(icon, item):
        # Prefer opening the friendly web settings page in the default browser.
        try:
            webbrowser.open('http://127.0.0.1:5000/settings', new=2)
        except Exception:
            # If the browser fails to open, fall back to the config folder.
            open_config_folder()

    # Static label to show basic server status
    status_item = pystray.MenuItem('Server Status: Running', lambda icon, item: None, enabled=False)

    menu = pystray.Menu(
        status_item,
        pystray.MenuItem('Settings', on_open_settings),
        pystray.MenuItem('Quit', on_quit)
    )

    icon = pystray.Icon(
        name='One-Click YouTube Downloader',
        title='One-Click YouTube Downloader',
        icon=create_tray_image(),
        menu=menu
    )

    print("[Tray] System tray running. Right-click the icon for options.")
    icon.run()


if __name__ == '__main__':
    # On Windows with a bundled .exe, auto-register for startup on boot
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        try:
            exe_path = sys.executable
            startup_dir = os.path.join(
                os.environ.get('APPDATA', ''),
                'Microsoft', 'Windows', 'Start Menu',
                'Programs', 'Startup'
            )
            vbs_path = os.path.join(startup_dir, 'YouTubeDownloader.vbs')
            if not os.path.exists(vbs_path):
                # Create a VBS script that launches the .exe silently (no terminal window)
                vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
                vbs_content += f'WshShell.Run Chr(34) & "{exe_path}" & Chr(34), 0, False\n'
                os.makedirs(startup_dir, exist_ok=True)
                with open(vbs_path, 'w') as f:
                    f.write(vbs_content)
                print("[Server] ✓ Auto-start configured! This app will now launch silently on every boot.")
            else:
                print("[Server] ✓ Auto-start already configured.")
        except Exception as e:
            print(f"[Server] Could not set up auto-start: {e}")

    download_dir = app_config.get('download_dir', '') or get_default_download_dir()
    print(f"[Server] Download folder: {os.path.expanduser(download_dir)}")
    print(f"[Server] Browser for cookies: {app_config.get('browser', 'auto')}")
    browser_name = get_active_browser()
    if browser_name:
        print(f"[Server] Detected browser: {browser_name}")
    else:
        print("[Server] No browser detected — cookies disabled")

    # Pre-extract cookies in background so the server starts INSTANTLY.
    # Cookie extraction can take a few seconds on fresh installs, so we run it once.
    threading.Thread(target=extract_cookies_to_file, daemon=True).start()

    # Check for and download the latest yt-dlp standalone binary in the background.
    # This keeps the bundled tool fresh without blocking startup.
    threading.Thread(target=download_latest_yt_dlp_binary, daemon=True).start()

    # Start Flask on a background thread so the main thread can own the tray.
    server_thread = FlaskServerThread(app, host='127.0.0.1', port=5000)
    server_thread.start()

    # Run the system tray icon on the main thread.
    run_tray(server_thread)

