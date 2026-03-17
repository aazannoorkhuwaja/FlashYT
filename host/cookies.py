import os
import sys
import glob
import subprocess
import shutil

# On Windows, suppress the black console popup for every subprocess spawned
_WIN_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
import time

from logger import log

import platform

def _get_config_dir():
    if platform.system() == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.config')
    config_dir = os.path.join(base, 'YouTubeNativeExt')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

COOKIE_FILE = os.path.join(_get_config_dir(), '.cached_cookies.txt')

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
        log.warning("[Cookies] No browser detected for cookie extraction")
        return False

    ytdlp_exe = _get_ytdlp_path()
    log.info(f"[Cookies] Attempting to extract cookies from browser: {browser}")

    try:
        cmd = [
            ytdlp_exe,
            '--cookies-from-browser', browser,
            '--cookies', COOKIE_FILE,
            '--skip-download',
            '--quiet',
            '--no-warnings',
            '--ignore-config',
            # Use YouTube homepage — no video format restriction checks.
            # A watch URL triggers 'Requested format is not available' even
            # with --skip-download, causing a corrupt/empty cookie file.
            'https://www.youtube.com/',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40, creationflags=_WIN_NO_WINDOW)
        if result.returncode != 0:
            log.error(f"[Cookies] yt-dlp cookie extraction failed: {result.stderr[:200]}")
            # Fallback: try the YouTube shorts feed (also has no format restriction)
            cmd[-1] = 'https://www.youtube.com/shorts/'
            result2 = subprocess.run(cmd, capture_output=True, text=True, timeout=40, creationflags=_WIN_NO_WINDOW)
            if result2.returncode != 0:
                log.error(f"[Cookies] yt-dlp cookie extraction fallback also failed: {result2.stderr[:200]}")

        if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 100:
            log.info(f"[Cookies] Successfully extracted cookies ({os.path.getsize(COOKIE_FILE)} bytes)")
            return True
        log.warning(f"[Cookies] Cookie file missing or too small after extraction")
        return False
    except subprocess.TimeoutExpired:
        log.error("[Cookies] Cookie extraction timed out after 40 seconds")
        return False
    except Exception as exc:
        log.error(f"[Cookies] Cookie extraction failed with exception: {exc}")
        return False


def save_injected_cookies(cookies_list):
    """
    Writes cookies provided by the extension to the cookie file in Netscape format.
    This is used to bypass Chromium's exclusive file lock on the cookies database on Windows.
    """
    if not cookies_list:
        return False
        
    try:
        lines = ["# Netscape HTTP Cookie File\n", "# http://curl.haxx.se/rfc/cookie_spec.html\n", "# This is a generated file!  Do not edit.\n\n"]
        for c in cookies_list:
            # Netscape format: domain, flag, path, secure, expiration, name, value
            domain = c.get('domain', '')
            # Field 2 is "Include Subdomains" (TRUE if it starts with a dot)
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = c.get('path', '/')
            secure = 'TRUE' if c.get('secure') else 'FALSE'
            expires = int(c.get('expires', 0))
            name = c.get('name', '')
            value = c.get('value', '')
            
            line = f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
            lines.append(line)
            
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        log.info(f"[Cookies] Successfully saved {len(cookies_list)} injected cookies to {COOKIE_FILE}")
        return True
    except Exception as exc:
        log.error(f"[Cookies] Failed to save injected cookies: {exc}")
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
