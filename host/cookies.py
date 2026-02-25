import os
import shutil
import tempfile
import time
import platform
import glob
from logger import log

BROWSER_PRIORITY = ['chrome', 'brave', 'edge', 'firefox', 'opera']

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
            paths.extend(glob.glob(os.path.join(app_data, r"Mozilla\Firefox\Profiles\*.default-release\cookies.sqlite")))
    elif system == "Darwin":
        if browser == 'chrome':
            paths.append(os.path.join(home, "Library/Application Support/Google/Chrome/Default/Cookies"))
        elif browser == 'brave':
            paths.append(os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies"))
        elif browser == 'edge':
            paths.append(os.path.join(home, "Library/Application Support/Microsoft Edge/Default/Cookies"))
        elif browser == 'firefox':
            paths.extend(glob.glob(os.path.join(home, "Library/Application Support/Firefox/Profiles/*.default-release/cookies.sqlite")))
    else: # Linux
        if browser == 'chrome':
            paths.append(os.path.join(home, ".config/google-chrome/Default/Cookies"))
        elif browser == 'brave':
            paths.append(os.path.join(home, ".config/BraveSoftware/Brave-Browser/Default/Cookies"))
        elif browser == 'edge':
            paths.append(os.path.join(home, ".config/microsoft-edge/Default/Cookies"))
        elif browser == 'firefox':
            paths.extend(glob.glob(os.path.join(home, ".mozilla/firefox/*.default-release/cookies.sqlite")))
            
    for db_path in paths:
        if os.path.exists(db_path):
            log.debug(f"[Cookies] Found database for {browser} at {db_path}")
            for attempt in range(2):
                try:
                    if browser == 'firefox':
                        shutil.copy2(db_path, os.path.join(target_dir, "cookies.sqlite"))
                    else:
                        shutil.copy2(db_path, os.path.join(target_dir, "Cookies"))
                        network_dir = os.path.join(target_dir, "Network")
                        os.makedirs(network_dir, exist_ok=True)
                        shutil.copy2(db_path, os.path.join(network_dir, "Cookies"))
                    log.debug(f"[Cookies] Copied cookie database for {browser} to temp directory")
                    return target_dir
                except Exception as e:
                    log.warning(f"[Cookies] Attempt {attempt+1} failed to copy {db_path}: {e}")
                    time.sleep(0.5)
                
    return None

def get_best_available_cookies():
    """
    Tries each browser in order and copies its cookie database to a temp dir.
    Returns a dict with 'browser' and 'profile_dir', or None if nothing found.

    NOTE: Cookie support is disabled by default in `download_video()` (cookie_dict = None).
    This function is only invoked if cookie support is explicitly re-enabled there.
    The code is intentionally kept to make re-enabling easy.
    """
    for browser in BROWSER_PRIORITY:
        temp_dir = tempfile.mkdtemp()
        try:
            profile_dir = copy_browser_cookies(browser, temp_dir)
            if profile_dir:
                log.info(f"[Cookies] Using {browser} cookies from shadow copy")
                return {"browser": browser, "profile_dir": profile_dir}
            else:
                # Cleanup if we didn't find the db
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            log.error(f"[Cookies] Error extracting cookies from {browser}: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    log.info("[Cookies] No browser cookies found or all extractions failed. Proceeding without cookies.")
    return None

def cleanup_cookie_dir(cookie_dict):
    """
    Cleans up the temporary directory created for shadow-copying cookies.
    """
    if cookie_dict and "profile_dir" in cookie_dict:
        try:
            shutil.rmtree(cookie_dict["profile_dir"], ignore_errors=True)
            log.debug(f"[Cookies] Cleaned up temporary profile dir {cookie_dict['profile_dir']}")
        except Exception:
            pass
