import sys
import threading
import subprocess
import os
import webbrowser
import json
import time
from urllib.request import Request, urlopen

from logger import log

HOST_VERSION = os.environ.get('FLASHYT_HOST_VERSION', '2.2.3')
RELEASE_API_URL = "https://api.github.com/repos/aazannoorkhuwaja/FlashYT/releases/latest"
RELEASES_URL = "https://github.com/aazannoorkhuwaja/FlashYT/releases/latest"
UPDATE_CHECK_INTERVAL_S = 6 * 60 * 60
YTDLP_UPDATE_INTERVAL_S = 24 * 60 * 60   # auto-update yt-dlp once a day
_YTDLP_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.ytdlp_updated')
_update_lock = threading.Lock()
_update_state = {
    "checking": False,
    "available": False,
    "latest": None,
    "url": RELEASES_URL,
    "error": None,
}


def _normalize_version(raw):
    src = (raw or "").strip().lower()
    if src.startswith("v"):
        src = src[1:]
    core = src.split("-")[0]
    parts = core.split(".")
    out = []
    for part in parts[:3]:
        try:
            out.append(int(part))
        except Exception:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return out


def _compare_versions(a, b):
    va = _normalize_version(a)
    vb = _normalize_version(b)
    for i in range(3):
        if va[i] > vb[i]:
            return 1
        if va[i] < vb[i]:
            return -1
    return 0


def _check_latest_release_once():
    with _update_lock:
        _update_state["checking"] = True
        _update_state["error"] = None
    try:
        req = Request(
            RELEASE_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "FlashYT-Host",
            },
        )
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        latest = (data.get("tag_name") or "").strip().lstrip("vV")
        url = data.get("html_url") or RELEASES_URL
        available = bool(latest) and _compare_versions(latest, HOST_VERSION) > 0
        with _update_lock:
            _update_state["latest"] = latest or None
            _update_state["url"] = url
            _update_state["available"] = available
            _update_state["error"] = None
    except Exception as e:
        with _update_lock:
            _update_state["error"] = str(e)
    finally:
        with _update_lock:
            _update_state["checking"] = False


def _get_ytdlp_path():
    """Find the yt-dlp binary (bundled alongside host files, or on PATH)."""
    # When running from a PyInstaller bundle the binary sits next to host.py
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(here, 'yt-dlp'),
        os.path.join(here, 'yt-dlp.exe'),
    ]:
        if os.path.isfile(candidate):
            return candidate
    # Fall back to PATH
    import shutil
    found = shutil.which('yt-dlp') or shutil.which('yt-dlp.exe')
    return found


_ytdlp_update_lock = threading.Lock()
_ytdlp_update_state = {"running": False, "last_run": 0.0, "last_result": ""}


def _update_ytdlp_now(on_finish=None):
    """Run 'yt-dlp --update' in a background thread. Safe to call from multiple threads."""
    with _ytdlp_update_lock:
        if _ytdlp_update_state["running"]:
            return  # already in progress
        _ytdlp_update_state["running"] = True

    def _run():
        try:
            ytdlp = _get_ytdlp_path()
            if not ytdlp:
                log.warning("[Tray] yt-dlp not found — cannot auto-update.")
                with _ytdlp_update_lock:
                    _ytdlp_update_state["last_result"] = "not_found"
                return

            log.info("[Tray] Running yt-dlp --update...")
            result = subprocess.run(
                [ytdlp, '--update'],
                capture_output=True, text=True, timeout=120
            )
            out = (result.stdout or '') + (result.stderr or '')
            updated = 'Updated yt-dlp' in out or 'Updating to' in out
            already_latest = 'up to date' in out.lower() or 'already up' in out.lower()
            if updated:
                log.info("[Tray] yt-dlp updated successfully.")
                result_str = "updated"
            elif already_latest:
                log.debug("[Tray] yt-dlp already up to date.")
                result_str = "latest"
            else:
                log.warning("[Tray] yt-dlp update had unexpected output: %s", out[:200])
                result_str = "unknown"

            now = time.time()
            with _ytdlp_update_lock:
                _ytdlp_update_state["last_run"] = now
                _ytdlp_update_state["last_result"] = result_str

            # Persist last-run timestamp so we don't re-update every restart
            try:
                with open(_YTDLP_STATE_FILE, 'w') as f:
                    f.write(str(now))
            except Exception:
                pass
        except subprocess.TimeoutExpired:
            log.error("[Tray] yt-dlp --update timed out.")
        except Exception as exc:
            log.error("[Tray] yt-dlp update failed: %s", exc)
        finally:
            with _ytdlp_update_lock:
                _ytdlp_update_state["running"] = False
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True).start()


def _schedule_ytdlp_auto_update():
    """Start background thread that updates yt-dlp once per day."""
    # Load last-run timestamp from disk
    last_run = 0.0
    try:
        if os.path.exists(_YTDLP_STATE_FILE):
            last_run = float(open(_YTDLP_STATE_FILE).read().strip())
    except Exception:
        pass

    with _ytdlp_update_lock:
        _ytdlp_update_state["last_run"] = last_run

    def _runner():
        # Stagger startup by 30s so host ping/prefetch completes first
        time.sleep(30)
        while True:
            with _ytdlp_update_lock:
                last = _ytdlp_update_state["last_run"]
            if time.time() - last >= YTDLP_UPDATE_INTERVAL_S:
                _update_ytdlp_now()
            time.sleep(60 * 60)  # check once an hour, update only daily

    threading.Thread(target=_runner, daemon=True).start()


def _start_update_checker():
    def _runner():
        _check_latest_release_once()
        while True:
            time.sleep(UPDATE_CHECK_INTERVAL_S)
            _check_latest_release_once()

    threading.Thread(target=_runner, daemon=True).start()


def create_tray_image():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    size = 64
    image = Image.new('RGBA', (size, size), (30, 30, 30, 255))
    draw = ImageDraw.Draw(image)

    margin = 8
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=12, fill=(204, 0, 0, 255)
    )
    triangle = [
        (size * 0.40, size * 0.32),
        (size * 0.40, size * 0.68),
        (size * 0.70, size * 0.50),
    ]
    draw.polygon(triangle, fill=(255, 255, 255, 255))
    return image


def start_tray_icon():
    try:
        import pystray
    except Exception as e:
        log.warning(f"[Tray] pystray/Pillow not installed or system lacks UI backend: {e}")
        return

    def on_quit(icon, item):
        log.info("[Tray] User selected Quit.")
        icon.stop()
        os._exit(0)

    def on_open_folder(icon, item):
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(downloads_dir)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', downloads_dir])
            else:
                subprocess.Popen(['xdg-open', downloads_dir])
        except Exception as e:
            log.error(f"[Tray] Failed to open folder: {e}")

    def on_view_log(icon, item):
        from logger import get_log_dir  # FIX 2: was "from .logger import get_log_dir"
        log_file = os.path.join(get_log_dir(), 'host.log')
        if not os.path.exists(log_file):
            return
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['notepad', log_file])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', log_file])
            else:
                subprocess.Popen(['xdg-open', log_file])
        except Exception as e:
            log.error(f"[Tray] Failed to view log: {e}")

    def get_update_label(item):
        with _update_lock:
            state = dict(_update_state)
        if state.get("checking"):
            return "Checking updates..."
        if state.get("available") and state.get("latest"):
            return f"Update available: v{state['latest']}"
        if state.get("latest"):
            return f"Up to date (v{HOST_VERSION})"
        if state.get("error"):
            return "Update check failed"
        return "Check for updates"

    def on_check_updates(icon, item):
        with _update_lock:
            url = _update_state.get("url") or RELEASES_URL
            checking = _update_state.get("checking")
            latest = _update_state.get("latest")
        if not checking and not latest:
            threading.Thread(target=_check_latest_release_once, daemon=True).start()
        webbrowser.open(url)

    def get_ytdlp_update_label(item):
        with _ytdlp_update_lock:
            state = dict(_ytdlp_update_state)
        if state.get("running"):
            return "  Updating yt-dlp..."
        if state.get("last_result") == "updated":
            return "  yt-dlp updated ✓"
        return "  Update yt-dlp Now"

    def on_update_ytdlp(icon, item):
        _update_ytdlp_now()

    menu = pystray.Menu(
        pystray.MenuItem(f'FlashYT v{HOST_VERSION}', lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(get_update_label, lambda i, it: None, enabled=False),
        pystray.MenuItem('Open Latest Release', on_check_updates),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(get_ytdlp_update_label, on_update_ytdlp),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Open Downloads Folder', on_open_folder),
        pystray.MenuItem('View Log File', on_view_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Quit', on_quit)
    )

    image = create_tray_image()
    if not image:
        return

    try:
        _start_update_checker()
        _schedule_ytdlp_auto_update()   # silent daily yt-dlp updater
        icon = pystray.Icon(
            name='FlashYT',
            title='FlashYT Native Host',
            icon=image,
            menu=menu
        )
        log.info("[Tray] Starting system tray icon...")
        threading.Thread(target=icon.run, daemon=True).start()
    except Exception as e:
        log.warning(f"[Tray] Failed to start system tray icon. Your desktop environment might not support it. Reason: {e}")
