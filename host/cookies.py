import os
import sys
import glob
import subprocess
import shutil
import time

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cached_cookies.txt')

BROWSER_PRIORITY = ['brave', 'chrome', 'chromium', 'firefox', 'edge', 'opera']

BROWSER_EXECUTABLES = {
    'brave':    ['brave-browser', 'brave'],
    'chrome':   ['google-chrome', 'google-chrome-stable'],
    'chromium': ['chromium-browser', 'chromium'],
    'firefox':  ['firefox'],
    'edge':     ['microsoft-edge', 'microsoft-edge-stable'],
    'opera':    ['opera'],
}


def _get_ytdlp_path():
    sys_path = shutil.which('yt-dlp')
    if sys_path:
        return sys_path
    if sys.platform == 'win32':
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        return os.path.join(base_dir, 'yt-dlp.exe')
    return '/usr/local/bin/yt-dlp' if os.path.exists('/usr/local/bin/yt-dlp') else '/usr/bin/yt-dlp'


def detect_browser():
    """Auto-detect first available browser from priority list."""
    for browser in BROWSER_PRIORITY:
        for exe in BROWSER_EXECUTABLES.get(browser, [browser]):
            if shutil.which(exe):
                return browser
    # Windows: check known install paths when executables are not in PATH
    if sys.platform == 'win32':
        localapp = os.environ.get('LOCALAPPDATA', '')
        win_paths = {
            'chrome': os.path.join(localapp, r'Google\\Chrome\\Application\\chrome.exe'),
            'brave':  os.path.join(localapp, r'BraveSoftware\\Brave-Browser\\Application\\brave.exe'),
            'edge':   os.path.join(localapp, r'Microsoft\\Edge\\Application\\msedge.exe'),
        }
        for browser, path in win_paths.items():
            if os.path.exists(path):
                return browser
    return None


def extract_cookies_to_file():
    """
    FIX: Uses yt-dlp CLI subprocess to extract and cache browser cookies to a
    Netscape-format cookie file.

    WHY THE OLD CODE WAS BROKEN:
      1. ydl.params['logger'] = logging.getLogger('devnull')
         yt-dlp expects an object with .debug()/.warning()/.error() methods
         matching its own signature — NOT a stdlib logging.Logger.
         This caused a TypeError on every prefetch that tried to log.

      2. cookie_jar = ydl.cookiejar; cookie_jar.save(...)
         yt-dlp lazy-loads cookies only during actual network requests.
         Just constructing YoutubeDL() returns an empty cookie jar.
         Calling .save() on an empty jar writes a useless header-only file.

    The subprocess approach is the only reliable cross-platform method.
    """
    browser = detect_browser()
    if not browser:
        return False

    ytdlp_exe = _get_ytdlp_path()

    try:
        cmd = [
            ytdlp_exe,
            '--cookies-from-browser', browser,
            '--cookies', COOKIE_FILE,
            '--skip-download',
            '--quiet',
            '--no-warnings',
            '--ignore-config',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        return os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 100
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def get_best_available_cookies():
    """
    Returns yt-dlp option dict for cookie auth.
    Refreshes the on-disk cache if it is missing or older than 1 hour.
    Falls back to live browser extraction if caching fails.
    """
    cache_age = (
        (time.time() - os.path.getmtime(COOKIE_FILE))
        if os.path.exists(COOKIE_FILE) else float('inf')
    )

    if cache_age > 3600:
        extract_cookies_to_file()

    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 100:
        return {'cookiefile': COOKIE_FILE}

    # Last resort: pass browser name for per-request extraction (3-5s overhead)
    browser = detect_browser()
    if browser:
        return {'cookiesfrombrowser': (browser, None, None, None)}

    return {}
