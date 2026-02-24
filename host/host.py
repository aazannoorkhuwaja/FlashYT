#!/usr/bin/env python3
import sys
import os
import json
import struct
import traceback
import queue
import threading
import subprocess

from logger import log

_stdout_lock = threading.Lock()

def send_message(msg):
    """
    Sends a serialized JSON message back to Chrome via stdout.
    MUST handle little-endian length prefix.
    """
    try:
        json_msg = json.dumps(msg)
        msg_bytes = json_msg.encode('utf-8')
        with _stdout_lock:
            sys.stdout.buffer.write(struct.pack('<I', len(msg_bytes)))
            sys.stdout.buffer.write(msg_bytes)
            sys.stdout.buffer.flush()
        log.debug(f"[Host] Sent: {json_msg}")
    except Exception as e:
        log.error(f"[Host] Error sending msg: {e}")

def read_message():
    """Reads a single message from Chrome via stdin."""
    try:
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            return None
            
        # Development override to allow standard 'echo' shell piping
        if raw_length[0] == ord('{'):
            rest = sys.stdin.buffer.read()
            msg_str = (raw_length + rest).decode('utf-8').strip()
            log.debug(f"[Host] Received raw un-prefixed test pipe: {msg_str}")
            return json.loads(msg_str)
            
        msg_length = struct.unpack('<I', raw_length)[0]
        msg_bytes = sys.stdin.buffer.read(msg_length)
        msg_str = msg_bytes.decode('utf-8')
        log.debug(f"[Host] Received raw: {msg_str}")
        return json.loads(msg_str)
    except Exception as e:
        log.error(f"[Host] Error reading msg: {e}")
        return None

def handle_task(msg):
    from downloader import prefetch_qualities, download_video
    downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    action = msg.get("type")
    
    try:
        if action == "prefetch":
            url = msg.get("url")
            if not url:
                send_message({"type": "error", "message": "No URL provided for prefetch."})
                return
                
            result = prefetch_qualities(url)
            send_message(result)
                
        elif action == "download":
            url = msg.get("url")
            itag = msg.get("itag")
            title = msg.get("title", "YouTube Video")
            
            if not url or not itag:
                send_message({"type": "error", "message": "Missing URL or format itag for download."})
                return
                
            def progress_callback(update_dict):
                send_message(update_dict)
                
            log.info(f"[Host] Beginning parallel download: {title}")
            result = download_video(url, itag, downloads_dir, progress_callback)
            send_message(result)
            
    except Exception as e:
        err_msg = traceback.format_exc()
        log.error(f"[Host] Unexpected worker error:\n{err_msg}")
        send_message({"type": "error", "message": "Internal error. Check host.log"})

def main():
    log.info("=" * 40)
    log.info("One-Click YT Downloader Host Started")
    log.info("=" * 40)
    
    try:
        from tray import start_tray_icon
        start_tray_icon()
    except Exception as e:
        log.warning(f"[Tray] System tray disabled (missing Linux bindings): {e}")

    # No longer using a blocking queue for downloads. 
    # Everything spawns directly into its own concurrent thread.
    active_threads = []

    try:
        while True:
            msg = read_message()
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
                if not target_path or not os.path.exists(target_path):
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
                    
            elif action in ["prefetch", "download"]:
                # Spawn concurrent download/prefetch thread instantly!
                t = threading.Thread(target=handle_task, args=(msg,), daemon=True)
                t.start()
                active_threads.append(t)
                
                # Cleanup dead threads from tracking list
                active_threads = [thread for thread in active_threads if thread.is_alive()]
                
            else:
                log.warning(f"[Host] Raw unhandled message type: {action}")
                send_message({"type": "error", "message": f"Unhandled message type: {action}"})
                
    except KeyboardInterrupt:
        log.info("[Host] Shutting down via KeyboardInterrupt.")
    except Exception as e:
        err_msg = traceback.format_exc()
        log.error(f"[Host] Fatal main loop error:\n{err_msg}")
    finally:
        log.info(f"[Host] Waiting for {len(active_threads)} active download threads to finish...")
        for t in active_threads:
            if t.is_alive():
                t.join(timeout=2.0)
        sys.exit(0)

if __name__ == '__main__':
    main()
