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
    Uses the cookie file injected by the browser extension.
    If no valid extension cookies are present, returns empty dict.
    """
    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 50:
        return {'cookiefile': COOKIE_FILE}

    return {}
