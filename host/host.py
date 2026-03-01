import json
import os
import queue
import struct
import subprocess
import sys
import threading
import time
import traceback

from logger import log

_stdout_lock = threading.Lock()
DEFAULT_DOWNLOAD_WORKERS = max(1, int(os.environ.get('FLASHYT_MAX_CONCURRENT', '3')))
DEFAULT_PREFETCH_WORKERS = max(1, int(os.environ.get('FLASHYT_PREFETCH_WORKERS', '2')))
_resume_wait_lock = threading.Lock()
_resume_waiting = set()
HOST_VERSION = os.environ.get('FLASHYT_HOST_VERSION', '2.1.1')


def send_message(msg):
    try:
        json_msg = json.dumps(msg)
        data = json_msg.encode('utf-8')
        with _stdout_lock:
            sys.stdout.buffer.write(struct.pack('<I', len(data)))
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    except Exception as exc:
        log.error('[Host] send_message failed: %s', exc)


def read_message():
    try:
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) == 0:
            return None

        if raw_length[0] == ord('{'):
            rest = sys.stdin.buffer.read()
            return json.loads((raw_length + rest).decode('utf-8').strip())

        msg_len = struct.unpack('<I', raw_length)[0]
        return json.loads(sys.stdin.buffer.read(msg_len).decode('utf-8'))
    except Exception as exc:
        log.error('[Host] read_message failed: %s', exc)
        return None


def _resolve_download_dir(path_hint):
    target = path_hint or os.path.join(os.path.expanduser('~'), 'Downloads')
    target = os.path.abspath(os.path.expanduser(target))
    os.makedirs(target, exist_ok=True)
    return target


def _progress_payload(update, download_id, video_id):
    return {
        'type': 'progress',
        'downloadId': download_id,
        'videoId': video_id,
        'percent': update.get('percent', '0%'),
        'speed': update.get('speed', ''),
        'eta': update.get('eta', ''),
    }


def _queue_resume_when_ready(download_id, download_queue):
    from downloader import resume_video

    # Thread safety fix: moved add operation inside the lock
    with _resume_wait_lock:
        if download_id in _resume_waiting:
            log.warning(f"[Host] Resume already waiting for download_id={download_id}")
            return
        _resume_waiting.add(download_id)
        log.debug(f"[Host] Added download_id={download_id} to resume waiting set")

    try:
        deadline = time.time() + 12
        while time.time() < deadline:
            ok, payload, info = resume_video(download_id)
            if ok and payload:
                download_queue.put(payload)
                return
            if not ok and info != 'No paused job found.':
                send_message({
                    'type': 'control_ack',
                    'action': 'resume',
                    'downloadId': download_id,
                    'ok': False,
                    'message': info,
                })
                return
            time.sleep(0.2)

        send_message({
            'type': 'control_ack',
            'action': 'resume',
            'downloadId': download_id,
            'ok': False,
            'message': 'Resume timed out while waiting for pause to complete.',
        })
    finally:
        with _resume_wait_lock:
            _resume_waiting.discard(download_id)


def prefetch_worker(prefetch_queue):
    from downloader import prefetch_qualities

    while True:
        msg = prefetch_queue.get()
        if msg is None:
            prefetch_queue.task_done()
            break

        try:
            url = msg.get('url')
            if not url:
                send_message({'type': 'prefetch_error', 'message': 'No URL provided for prefetch.', 'reqUrl': url})
                continue

            result = prefetch_qualities(url)
            if result.get('error'):
                send_message({'type': 'prefetch_error', 'message': result['error'], 'reqUrl': url})
            else:
                out = {'type': 'prefetch_result', 'reqUrl': url}
                out.update(result)
                send_message(out)
        except Exception:
            log.error('[Host] prefetch_worker exception:\n%s', traceback.format_exc())
            send_message({'type': 'prefetch_error', 'message': 'Prefetch failed unexpectedly.'})
        finally:
            prefetch_queue.task_done()


def download_worker(download_queue):
    from downloader import download_video

    while True:
        msg = download_queue.get()
        if msg is None:
            download_queue.task_done()
            break

        try:
            url = msg.get('url')
            itag = msg.get('itag')
            download_id = msg.get('downloadId')
            video_id = msg.get('videoId')
            real_itag = msg.get('real_itag')
            save_location = _resolve_download_dir(msg.get('save_location'))

            if not url or not itag:
                send_message({
                    'type': 'error',
                    'downloadId': download_id,
                    'videoId': video_id,
                    'message': 'Missing URL or format itag for download.',
                })
                continue

            def progress_cb(update):
                send_message(_progress_payload(update, download_id, video_id))

            result = download_video(
                url,
                itag,
                save_location,
                progress_cb,
                download_id=download_id,
                video_id=video_id,
                real_itag=real_itag,
            )
            send_message(result)
        except Exception:
            log.error('[Host] download_worker exception:\n%s', traceback.format_exc())
            send_message({'type': 'error', 'message': 'Download failed unexpectedly.'})
        finally:
            download_queue.task_done()


def main():
    from downloader import cancel_video, pause_video, resume_video
    from tray import start_tray_icon

    start_tray_icon()

    prefetch_queue = queue.Queue()
    download_queue = queue.Queue()
    prefetch_workers = DEFAULT_PREFETCH_WORKERS
    for _ in range(prefetch_workers):
        threading.Thread(target=prefetch_worker, args=(prefetch_queue,), daemon=True).start()
    worker_count = DEFAULT_DOWNLOAD_WORKERS
    for _ in range(worker_count):
        threading.Thread(target=download_worker, args=(download_queue,), daemon=True).start()

    try:
        while True:
            msg = read_message()
            if msg is None:
                break

            action = msg.get('type')
            if action == 'ping':
                send_message({'type': 'pong', 'version': HOST_VERSION})

            elif action == 'open_folder':
                target_path = msg.get('path')
                if not target_path or not os.path.exists(target_path):
                    target_path = _resolve_download_dir(None)
                try:
                    if sys.platform == 'win32':
                        os.startfile(target_path)
                    elif sys.platform == 'darwin':
                        subprocess.Popen(['open', target_path])
                    else:
                        subprocess.Popen(['xdg-open', target_path])
                    send_message({'type': 'ok'})
                except Exception as exc:
                    send_message({'type': 'error', 'message': f'Failed to open folder: {exc}'})

            elif action == 'prefetch':
                prefetch_queue.put(msg)

            elif action == 'download':
                download_queue.put(msg)

            elif action == 'pause':
                download_id = msg.get('downloadId')
                ok, info = pause_video(download_id)
                send_message({'type': 'control_ack', 'action': 'pause', 'downloadId': download_id, 'ok': ok, 'message': info})

            elif action == 'resume':
                download_id = msg.get('downloadId')
                ok, payload, info = resume_video(download_id)
                if ok and payload:
                    download_queue.put(payload)
                elif ok and not payload:
                    threading.Thread(target=_queue_resume_when_ready, args=(download_id, download_queue), daemon=True).start()
                send_message({'type': 'control_ack', 'action': 'resume', 'downloadId': download_id, 'ok': ok, 'message': info})

            elif action == 'cancel':
                download_id = msg.get('downloadId')
                ok, info = cancel_video(download_id)
                send_message({'type': 'control_ack', 'action': 'cancel', 'downloadId': download_id, 'ok': ok, 'message': info})

            elif action == 'self_update':
                def _run_self_update():
                    try:
                        send_message({'type': 'self_update_progress', 'status': 'started',
                                      'message': 'Downloading latest FlashYT update...'})
                        if sys.platform == 'win32':
                            # On Windows, open the releases page — bash not available
                            import webbrowser
                            webbrowser.open('https://github.com/aazannoorkhuwaja/FlashYT/releases/latest')
                            send_message({'type': 'self_update_progress', 'status': 'done',
                                          'message': 'Opened releases page. Download and run the new installer.'})
                        else:
                            result = subprocess.run(
                                ['bash', '-c',
                                 'curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash'],
                                capture_output=True, text=True, timeout=120
                            )
                            if result.returncode == 0:
                                send_message({'type': 'self_update_progress', 'status': 'done',
                                              'message': 'Update complete! Please reload the extension.'})
                            else:
                                err = (result.stderr or result.stdout or 'Unknown error')[-200:]
                                send_message({'type': 'self_update_progress', 'status': 'error',
                                              'message': f'Update failed: {err}'})
                    except subprocess.TimeoutExpired:
                        send_message({'type': 'self_update_progress', 'status': 'error',
                                      'message': 'Update timed out. Check your internet connection.'})
                    except Exception as exc:
                        send_message({'type': 'self_update_progress', 'status': 'error',
                                      'message': f'Update error: {exc}'})
                threading.Thread(target=_run_self_update, daemon=True).start()

            else:
                send_message({'type': 'error', 'message': f'Unhandled message type: {action}'})
    except KeyboardInterrupt:
        pass
    except Exception:
        log.error('[Host] fatal:\n%s', traceback.format_exc())
    finally:
        for _ in range(prefetch_workers):
            prefetch_queue.put(None)
        for _ in range(worker_count):
            download_queue.put(None)
        prefetch_queue.join()
        download_queue.join()
        sys.exit(0)


if __name__ == '__main__':
    main()
