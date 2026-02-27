import sys
import threading
import subprocess
import os
import webbrowser

from logger import log  # FIX 1: was "from .logger import log" – relative import fails


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

    def on_check_updates(icon, item):
        webbrowser.open("https://github.com/aazannoorkhuwaja/FlashYT/releases")

    menu = pystray.Menu(
        pystray.MenuItem('FlashYT v1.0.0', lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Open Downloads Folder', on_open_folder),
        pystray.MenuItem('View Log File', on_view_log),
        pystray.MenuItem('Check for Updates', on_check_updates),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Quit', on_quit)
    )

    image = create_tray_image()
    if not image:
        return

    try:
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
