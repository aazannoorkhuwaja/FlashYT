#!/usr/bin/env python3
# --- Top-level imports (explicit dependency graph) ---
import sys
import os
import json
import struct
import traceback
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from logger import log
from downloader import prefetch_qualities, download_video, update_ytdlp

# -------------------------------------------------------
# Global lifecycle flag — threads check this before writing
# to stdout to prevent BrokenPipeError deadlocks on shutdown.
# -------------------------------------------------------
_host_alive = True
_stdout_lock = threading.Lock()

# Allowed YouTube hostnames — urlparse check prevents spoofing via query parameters.
# e.g. https://evil.com/?redirect=youtube.com would bypass a naive substring 'in url' check.
_YOUTUBE_HOSTS = frozenset({'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'})

def _is_youtube_url(url):
    """Returns True only if the URL hostname is a known YouTube domain."""
    try:
        return urlparse(url).netloc.lower() in _YOUTUBE_HOSTS
    except Exception:
        return False

def send_message(msg):
    """
    Sends a serialized JSON message back to Chrome via stdout.
    MUST handle little-endian length prefix.
    Returns False silently if the host is shutting down.
    """
    if not _host_alive:
        return False
    try:
        json_msg = json.dumps(msg)
        msg_bytes = json_msg.encode('utf-8')
        with _stdout_lock:
            sys.stdout.buffer.write(struct.pack('<I', len(msg_bytes)))
            sys.stdout.buffer.write(msg_bytes)
            sys.stdout.buffer.flush()
        log.debug(f"[Host] Sent: {json_msg}")
        return True
    except BrokenPipeError:
        log.warning("[Host] Stdout pipe closed (Chrome disconnected). Stopping outbound messages.")
        return False
    except Exception as e:
        log.error(f"[Host] Error sending msg: {e}")
        return False

def read_message(dev_mode=False):
    """
    Reads a single message from Chrome via stdin.
    In --dev-mode, accepts plain JSON from echo pipes (for CLI testing only).
    In production, strictly enforces the Chrome Native Messaging 4-byte LE prefix protocol.
    """
    try:
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            return None

        if dev_mode:
            # Explicit dev-mode path: read rest of the pipe as plain JSON
            rest = sys.stdin.buffer.read()
            msg_str = (raw_length + rest).decode('utf-8').strip()
            log.debug(f"[Host] DEV MODE raw pipe: {msg_str}")
            return json.loads(msg_str)

        # Production path: enforce Chrome's strict little-endian 4-byte length prefix
        msg_length = struct.unpack('<I', raw_length)[0]
        msg_bytes = sys.stdin.buffer.read(msg_length)
        msg_str = msg_bytes.decode('utf-8')
        log.debug(f"[Host] Received raw: {msg_str}")
        return json.loads(msg_str)
    except Exception as e:
        log.error(f"[Host] Error reading msg: {e}")
        return None

def handle_task(msg):
    downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    action = msg.get("type")

    try:
        if action == "prefetch":
            url = msg.get("url")
            if not url or not _is_youtube_url(url):
                send_message({"type": "error", "message": "Invalid YouTube URL."})
                return

            result = prefetch_qualities(url)
            send_message(result)

        elif action == "download":
            url = msg.get("url")
            max_height = msg.get("max_height")
            title = msg.get("title", "YouTube Video")

            if not url or not _is_youtube_url(url):
                send_message({"type": "error", "message": "Invalid YouTube URL."})
                return

            if not max_height:
                send_message({"type": "error", "message": "Missing format height for download."})
                return

            def progress_callback(update_dict):
                send_message(update_dict)

            log.info(f"[Host] Beginning parallel download: {title}")
            result = download_video(url, max_height, downloads_dir, progress_callback)
            send_message(result)

        elif action == "update_engine":
            def progress_callback(update_dict):
                send_message(update_dict)
            log.info("[Host] Initiating manual yt-dlp core auto-update sequence.")
            result = update_ytdlp(progress_callback)
            send_message(result)

    except Exception as e:
        err_msg = traceback.format_exc()
        log.error(f"[Host] Unexpected worker error:\n{err_msg}")
        send_message({"type": "error", "message": "Internal error. Check host.log"})

def main():
    global _host_alive

    # Parse --dev-mode CLI flag explicitly (never passed by Chrome installer)
    dev_mode = "--dev-mode" in sys.argv

    log.info("=" * 40)
    log.info("One-Click YT Downloader Host Started")
    if dev_mode:
        log.info("[Host] *** DEV MODE ACTIVE — plain JSON stdin accepted ***")
    log.info("=" * 40)

    try:
        from tray import start_tray_icon
        start_tray_icon()
    except Exception as e:
        log.warning(f"[Tray] System tray disabled (missing Linux bindings): {e}")

    # ThreadPoolExecutor bounds concurrent downloads and handles lifecycle automatically.
    # max_workers=8 allows plenty of parallel downloads without exhausting system resources.
    executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ytdl_worker")

    try:
        while True:
            msg = read_message(dev_mode=dev_mode)
            if msg is None:
                log.info("[Host] Extension closed the pipe. Exiting.")
                break

            action = msg.get("type")
            if not action:
                continue

            if action == "ping":
                send_message({"type": "pong", "version": "1.0.0"})

            elif action == "open_folder":
                target_path = msg.get("path")

                # Resolve special sentinel paths
                if not target_path or target_path == "LOG_DIR":
                    if sys.platform == 'win32':
                        target_path = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'YouTubeNativeExt')
                    else:
                        target_path = os.path.join(os.path.expanduser('~'), '.config', 'YouTubeNativeExt')

                if not os.path.exists(target_path):
                    target_path = os.path.join(os.path.expanduser('~'), 'Downloads')
                    os.makedirs(target_path, exist_ok=True)

                try:
                    if sys.platform == 'win32':
                        os.startfile(target_path)
                    elif sys.platform == 'darwin':
                        subprocess.Popen(['open', target_path])
                    else:
                        subprocess.Popen(['xdg-open', target_path])
                    send_message({"type": "ok"})
                except Exception as e:
                    send_message({"type": "error", "message": f"Failed to open folder: {e}"})

            elif action in ["prefetch", "download", "update_engine"]:
                # Submit task to the bounded thread pool
                executor.submit(handle_task, msg)

            else:
                log.warning(f"[Host] Raw unhandled message type: {action}")
                send_message({"type": "error", "message": f"Unhandled message type: {action}"})

    except KeyboardInterrupt:
        log.info("[Host] Shutting down via KeyboardInterrupt.")
    except Exception as e:
        err_msg = traceback.format_exc()
        log.error(f"[Host] Fatal main loop error:\n{err_msg}")
    finally:
        # Signal all worker threads to stop writing to the closed pipe
        _host_alive = False
        log.info("[Host] Waiting for active download workers to finish...")
        # wait=True lets in-flight downloads complete; cancel_futures=False is default
        executor.shutdown(wait=True)
        sys.exit(0)

if __name__ == '__main__':
    main()
