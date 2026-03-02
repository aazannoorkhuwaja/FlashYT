import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque

from constants import DEFAULT_USER_AGENT
from cookies import detect_browser, get_best_available_cookies, extract_cookies_to_file
from fast_fetch import prefetch_qualities_fast
from logger import log

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_re_pct = re.compile(r'\[download\]\s+(\d+\.?\d*%)\s+of')
_re_speed = re.compile(r'at\s+([\d.]+\s*\w+i?B/s)')
_re_eta = re.compile(r'ETA\s+([\d:~]+)')
_re_aria2 = re.compile(r'(\d+\.?\d*%)')

_active_lock = threading.Lock()
active_processes = {}
paused_jobs = {}


def _terminate_process_tree(proc, timeout_s=3):
    if proc.poll() is not None:
        return True

    try:
        if sys.platform == 'win32':
            proc.terminate()
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()

        deadline = time.time() + timeout_s
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)

        if proc.poll() is None:
            if sys.platform == 'win32':
                proc.kill()
            else:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
        return proc.poll() is not None
    except Exception as exc:
        log.warning('[Downloader] terminate process tree failed: %s', exc)
        return False


def get_ytdlp_path():
    sys_path = shutil.which('yt-dlp')
    if sys_path:
        log.debug(f"[Downloader] Found yt-dlp at: {sys_path}")
        return sys_path
    if sys.platform == 'win32':
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        path = os.path.join(base_dir, 'yt-dlp.exe')
        if os.path.exists(path):
            log.debug(f"[Downloader] Found yt-dlp at (frozen): {path}")
            return path
    # Check common Linux paths
    for candidate in ['/usr/local/bin/yt-dlp', '/usr/bin/yt-dlp']:
        if os.path.exists(candidate):
            log.debug(f"[Downloader] Found yt-dlp at: {candidate}")
            return candidate
    log.error("[Downloader] yt-dlp not found! Please install yt-dlp.")
    return None


def get_ffmpeg_path():
    sys_path = shutil.which('ffmpeg')
    if sys_path:
        log.debug(f"[Downloader] Found ffmpeg at: {sys_path}")
        return sys_path
    if sys.platform == 'win32':
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        path = os.path.join(base_dir, 'ffmpeg.exe')
        if os.path.exists(path):
            log.debug(f"[Downloader] Found ffmpeg at (frozen): {path}")
            return path
    # Check common Linux paths
    for candidate in ['/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg']:
        if os.path.exists(candidate):
            log.debug(f"[Downloader] Found ffmpeg at: {candidate}")
            return candidate
    log.warning("[Downloader] ffmpeg not found! Merging may fail.")
    return None


def _build_video_format_string(max_height):
    try:
        h = int(max_height)
    except (TypeError, ValueError):
        h = 1080
    return (
        f"bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[vcodec^=avc][height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"bestvideo[height<={h}]/"
        "bestvideo+bestaudio/bestvideo"
    )


def _resolve_output_dir(path_hint):
    target = path_hint or os.path.join(os.path.expanduser('~'), 'Downloads')
    target = os.path.abspath(os.path.expanduser(target))
    os.makedirs(target, exist_ok=True)
    return target


def _extract_ydlp_error(log_tail):
    msg = 'yt-dlp encountered an error.'
    for err_line in reversed(log_tail):
        if 'ERROR:' in err_line:
            msg = err_line.split('ERROR:', 1)[1].strip()
            break
        if err_line.lower().startswith('error:'):
            msg = err_line.split(':', 1)[1].strip()
            break
    return msg


def _is_format_unavailable_error(message):
    text = (message or '').lower()
    return (
        'requested format is not available' in text
        or 'requested format not available' in text
        or 'format is not available' in text
        or 'no video formats found' in text
    )


def _is_auth_or_access_error(message):
    text = (message or '').lower()
    return (
        'sign in to confirm' in text
        or 'not a bot' in text
        or 'unable to download api page' in text
        or 'http error 403' in text
        or 'forbidden' in text
    )


def _parse_height_from_itag(itag, default=1080):
    if isinstance(itag, str) and itag.startswith('video_'):
        try:
            return int(itag.split('_')[1])
        except Exception:
            return default
    return default


def _canonicalize_youtube_url(url):
    if not url:
        return url
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", url)
    if not m:
        return url
    return f"https://www.youtube.com/watch?v={m.group(1)}"


def _prefetch_with_timeout(url, timeout_s=8):
    result_box = {'result': None}

    def _runner():
        try:
            result_box['result'] = prefetch_qualities_fast(url)
        except Exception as exc:
            result_box['result'] = {'error': f'Fast prefetch failed: {exc}'}

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        return {'error': 'Prefetch timed out. Retrying with fallback...'}
    return result_box['result'] or {'error': 'Empty prefetch result.'}


def _prefetch_with_ytdlp(url, timeout_s=20):
    canonical_url = _canonicalize_youtube_url(url)
    base_cmd = [
        get_ytdlp_path(),
        '--no-playlist',
        '--ignore-config',
        '--no-warnings',
        '--skip-download',
        '--dump-json',
    ]

    cookie_opts = get_best_available_cookies()
    cookie_args = []
    if 'cookiefile' in cookie_opts:
        cookie_args = ['--cookies', cookie_opts['cookiefile']]
    elif cookie_opts.get('cookiesfrombrowser'):
        browser = cookie_opts['cookiesfrombrowser'][0]
        cookie_args = ['--cookies-from-browser', browser]
    else:
        browser = detect_browser()
        if browser:
            cookie_args = ['--cookies-from-browser', browser]

    profiles = [
        [],
        ['--allow-unplayable-formats'],
        ['--extractor-args', 'youtube:player_client=web,ios,android'],
        ['--allow-unplayable-formats', '--extractor-args', 'youtube:player_client=web,ios,android'],
        ['-f', 'bestvideo+bestaudio/best'],
    ]

    deadline = time.time() + timeout_s
    last_error = 'Fallback prefetch failed.'
    data = None
    for profile in profiles:
        remaining = deadline - time.time()
        if remaining <= 0:
            last_error = 'Fallback prefetch timed out.'
            break
        profile_timeout = max(3, min(8, int(remaining)))
        cmd = base_cmd + profile + cookie_args + [canonical_url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=profile_timeout)
        except Exception as exc:
            last_error = f'Fallback prefetch exception: {exc}'
            continue

        if proc.returncode != 0 or not (proc.stdout or '').strip():
            err = (proc.stderr or '').strip()
            if err:
                last_error = f'Fallback prefetch failed. {err[:300]}'
            continue

        try:
            data = json.loads(proc.stdout)
            break
        except Exception as exc:
            last_error = f'Fallback prefetch parse exception: {exc}'
            continue

    if data is None:
        return {'error': last_error}

    try:
        formats = data.get('formats', [])
        title = data.get('title', 'Unknown Video')

        best_by_height = {}
        for f in formats:
            height = f.get('height')
            if not height:
                continue
            if f.get('vcodec') in (None, 'none'):
                continue
            if height not in best_by_height or (f.get('tbr') or 0) > (best_by_height[height].get('tbr') or 0):
                best_by_height[height] = f

        qualities = []
        for h in sorted(best_by_height.keys(), reverse=True):
            fmt = best_by_height[h]
            size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
            size_mb = round(size / (1024 * 1024), 1) if size else 0
            qualities.append({
                'label': f'{h}p',
                'quality_label': f'{h}p',
                'itag': f'video_{h}',
                'real_itag': fmt.get('format_id'),
                'fps': fmt.get('fps', 30),
                'ext': fmt.get('ext', 'mp4'),
                'size_mb': size_mb,
            })

        if not qualities:
            return {'error': 'No downloadable qualities found.'}
        return {'title': title, 'qualities': qualities, 'duration': int(data.get('duration') or 0)}
    except Exception as exc:
        return {'error': f'Fallback prefetch exception: {exc}'}


_YOUTUBE_API_CHANGE_SIGNALS = [
    'sign in', 'login', 'please sign', 'not available',
    'update yt-dlp', 'outdated', 'nsig extraction',
    'unable to extract', 'http error 403', 'http error 429',
    'video unavailable', 'could not fetch', 'no formats',
]

def _looks_like_youtube_api_change(error_msg: str) -> bool:
    """Return True if the error message suggests YouTube changed their API."""
    t = (error_msg or '').lower()
    return any(sig in t for sig in _YOUTUBE_API_CHANGE_SIGNALS)


def prefetch_qualities(url):
    hint = 'If this persists, sign in to YouTube in your browser and restart FlashYT.'

    def with_hint(msg):
        msg = (msg or '').strip()
        if hint in msg:
            return msg
        return f'{msg} {hint}'.strip()

    # Stage 1: fast InnerTube (1-2s)
    fast_result = _prefetch_with_timeout(url, timeout_s=8)
    if fast_result and not fast_result.get('error') and fast_result.get('qualities'):
        return fast_result

    # Stage 2: yt-dlp fallback (up to 25s)
    fallback = _prefetch_with_ytdlp(url, timeout_s=25)
    if fallback and not fallback.get('error') and fallback.get('qualities'):
        return fallback

    # Stage 3: if everything failed and it looks like a YouTube API change,
    # trigger an immediate yt-dlp self-update then retry once.
    fast_err = (fast_result or {}).get('error', '')
    fall_err = (fallback or {}).get('error', '')
    combined_err = f'{fast_err} {fall_err}'

    if _looks_like_youtube_api_change(combined_err):
        log.warning('[Downloader] YouTube API change detected. Triggering yt-dlp self-update and retrying...')
        import threading, time as _time
        try:
            from tray import _update_ytdlp_now, _ytdlp_update_state, _ytdlp_update_lock
            done_event = threading.Event()
            _update_ytdlp_now(on_finish=done_event.set)
            # Wait up to 90s for update to finish
            done_event.wait(timeout=90)
        except Exception as upd_exc:
            log.warning('[Downloader] Could not trigger yt-dlp update: %s', upd_exc)

        # Retry yt-dlp now that it's (hopefully) updated
        retry = _prefetch_with_ytdlp(url, timeout_s=35)
        if retry and not retry.get('error') and retry.get('qualities'):
            log.info('[Downloader] Retry after yt-dlp update succeeded.')
            return retry
        if retry and retry.get('error'):
            return {'error': with_hint(f'YouTube may have changed their API. yt-dlp was auto-updated — please try again: {retry["error"]}')}

    if fallback and fallback.get('error'):
        return {'error': with_hint(fallback['error'])}
    if fast_result and fast_result.get('error'):
        return {'error': with_hint(fast_result['error'])}
    return {'error': with_hint('Failed to prefetch qualities.')}


def _build_download_cmd(url, itag, output_dir, download_id, real_itag, retry_stage=0):
    ffmpeg_path = get_ffmpeg_path()
    cmd = [
        get_ytdlp_path(),
        '--no-playlist',
        '--ignore-config',
        '--newline',
        '--no-warnings',
        '--no-update',
        '--no-check-certificate',
        '--user-agent', DEFAULT_USER_AGENT,
        '--continue',
        '--part',
        '--progress',
        '--cache-dir', os.path.join(os.path.expanduser('~'), '.flashyt_cache', download_id or 'default'),
        '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
    ]
    if ffmpeg_path:
        cmd[1:1] = ['--ffmpeg-location', ffmpeg_path]

    # Only force specific extractor clients on non-universal fallback.
    # On retry_stage=2 (universal), let yt-dlp pick its own client — forcing
    # web,ios,android was causing YouTube to block some format requests.
    if retry_stage < 2:
        cmd.extend(['--extractor-args', 'youtube:player_client=web,ios,android'])

    # Validate cookie file has real content before using it (>200 bytes).
    # A stale/empty/header-only cookie file causes YouTube to deny all formats.
    cookie_opts = get_best_available_cookies()
    cookie_file = cookie_opts.get('cookiefile')
    use_cookiefile = (
        cookie_file
        and os.path.isfile(cookie_file)
        and os.path.getsize(cookie_file) > 200
    )

    if use_cookiefile:
        cmd.extend(['--cookies', cookie_file])
    elif cookie_opts.get('cookiesfrombrowser'):
        browser = cookie_opts['cookiesfrombrowser'][0]
        cmd.extend(['--cookies-from-browser', browser])
    elif retry_stage < 2:
        # Only attempt live browser cookie extraction on non-universal retries
        browser = detect_browser()
        if browser:
            cmd.extend(['--cookies-from-browser', browser])
    # On retry_stage=2 (universal): no cookies at all — cleanest fallback

    if itag == 'audio_only':
        # Let yt-dlp resolve the best audio format fresh — no stale itag needed.
        cmd.extend(['-f', 'bestaudio[ext=m4a]/bestaudio/best', '--extract-audio', '--audio-format', 'mp3'])
    elif isinstance(itag, str) and itag.startswith('video_'):
        # Use a height-based selector so yt-dlp fetches a fresh format ID internally.
        # real_itag tokens expire within seconds and cause the 0% retry loop — never use them.
        h = _parse_height_from_itag(itag)
        cmd.extend([
            '-f', _build_video_format_string(h),
            '--merge-output-format', 'mp4',
        ])
    # For __auto_best__ (universal fallback): no -f flag, let yt-dlp decide

    # Capture the actual downloaded resolution for the quality badge in the UI.
    cmd.extend(['--print', '%(height)s'])

    cmd.append(url)
    return cmd


def pause_video(download_id):
    if not download_id:
        return False, 'Missing download ID.'

    with _active_lock:
        entry = active_processes.get(download_id)
        if not entry:
            if download_id in paused_jobs:
                return True, 'Already paused.'
            return False, 'Download not running.'

        if entry.get('stop_reason') == 'paused':
            return True, 'Pause already requested.'
        entry['stop_reason'] = 'paused'
        proc = entry['proc']

    if _terminate_process_tree(proc):
        return True, 'Pause requested.'
    return False, 'Pause failed while stopping process.'


def resume_video(download_id):
    if not download_id:
        return False, None, 'Missing download ID.'

    with _active_lock:
        active = active_processes.get(download_id)
        if active:
            if active.get('stop_reason') == 'paused':
                return True, None, 'Pause in progress. Resume queued.'
            return False, None, 'Already active.'
        job = paused_jobs.pop(download_id, None)

    if not job:
        return False, None, 'No paused job found.'

    payload = {
        'type': 'download',
        'url': job.get('url'),
        'itag': job.get('itag'),
        'downloadId': job.get('downloadId') or job.get('download_id') or download_id,
        'videoId': job.get('videoId') or job.get('video_id'),
        'real_itag': job['real_itag'],
        'save_location': job.get('save_location') or job.get('output_dir'),
        'resume': True,
    }
    return True, payload, 'Resume requested.'


def cancel_video(download_id):
    if not download_id:
        return False, 'Missing download ID.'

    with _active_lock:
        paused_jobs.pop(download_id, None)
        entry = active_processes.get(download_id)
        if not entry:
            return True, 'Already inactive.'
        entry['stop_reason'] = 'cancelled'
        proc = entry['proc']

    if _terminate_process_tree(proc):
        return True, 'Cancel requested.'
    return False, 'Cancel failed while stopping process.'


def download_video(
    url,
    itag,
    output_dir,
    progress_callback,
    download_id=None,
    video_id=None,
    real_itag=None,
    retry_stage=0,
):
    if not url or not itag:
        return {'type': 'error', 'downloadId': download_id, 'videoId': video_id, 'message': 'Missing URL or format.'}

    download_id = download_id or f'dl_{int(time.time() * 1000)}'
    resolved_output = _resolve_output_dir(output_dir)

    cmd = _build_download_cmd(url, itag, resolved_output, download_id, real_itag, retry_stage=retry_stage)
    log.debug('[Downloader] Starting: %s', ' '.join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
        start_new_session=(sys.platform != 'win32'),
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0),
    )

    job_state = {
        'url': url,
        'itag': itag,
        'downloadId': download_id,
        'videoId': video_id,
        'real_itag': real_itag,
        'save_location': resolved_output,
    }

    with _active_lock:
        active_processes[download_id] = {'proc': process, 'stop_reason': None, 'job_state': job_state}

    destination_regex = re.compile(r'\[(?:download|Merger|ExtractAudio)\]\s+Destination:\s+(.*)')
    already_downloaded_regex = re.compile(r'\[download\]\s+(.*)\s+has already been downloaded')

    last_filename = ''
    actual_quality = ''
    already_exists = False
    last_progress = [time.time()]
    log_tail = deque(maxlen=200)
    _re_print_height = re.compile(r'^(\d+)$')

    def monitor_hang(proc, stamp, timeout=90):
        while proc.poll() is None:
            if time.time() - stamp[0] > timeout:
                _terminate_process_tree(proc, timeout_s=1)
                break
            time.sleep(2)

    threading.Thread(target=monitor_hang, args=(process, last_progress), daemon=True).start()

    try:
        for line in iter(process.stdout.readline, ''):
            last_progress[0] = time.time()
            clean = ansi_escape.sub('', line).strip()
            if not clean:
                continue
            log_tail.append(clean)

            dest_match = destination_regex.search(clean)
            if dest_match:
                last_filename = os.path.basename(dest_match.group(1).strip().strip('"'))
                continue

            # yt-dlp --print %(height)s outputs the height on a line by itself before download starts.
            if not actual_quality:
                ph = _re_print_height.match(clean)
                if ph:
                    actual_quality = f'{ph.group(1)}p'
                    continue

            already_match = already_downloaded_regex.search(clean)
            if already_match:
                already_exists = True
                last_filename = os.path.basename(already_match.group(1).strip().strip('"'))
                progress_callback({'percent': '100%', 'speed': 'Done', 'eta': ''})
                continue

            pct_match = _re_pct.search(clean) or _re_aria2.search(clean)
            if pct_match:
                speed_match = _re_speed.search(clean)
                eta_match = _re_eta.search(clean)
                progress_callback({
                    'percent': pct_match.group(1),
                    'speed': speed_match.group(1) if speed_match else '',
                    'eta': eta_match.group(1) if eta_match else '',
                })
            elif 'merger' in clean.lower() or 'ffmpeg' in clean.lower():
                progress_callback({'percent': '99%', 'speed': 'Processing', 'eta': ''})

        process.stdout.close()
        process.wait()

        with _active_lock:
            entry = active_processes.pop(download_id, None)
            stop_reason = entry.get('stop_reason') if entry else None

        if stop_reason == 'paused':
            with _active_lock:
                paused_jobs[download_id] = job_state
            return {'type': 'paused', 'downloadId': download_id, 'videoId': video_id, 'message': 'Download paused.'}
        if stop_reason == 'cancelled':
            return {'type': 'cancelled', 'downloadId': download_id, 'videoId': video_id, 'message': 'Download cancelled.'}

        if process.returncode != 0:
            msg = _extract_ydlp_error(log_tail)
            # Real itags can go stale quickly; retry once with adaptive selector.
            if real_itag and retry_stage == 0 and _is_format_unavailable_error(msg):
                progress_callback({'percent': '0%', 'speed': 'Retrying with available quality', 'eta': ''})
                log.warning(
                    '[Downloader] real_itag=%s unavailable for %s. Retrying with adaptive format.',
                    real_itag,
                    url,
                )
                retry_result = download_video(
                    url,
                    itag,
                    resolved_output,
                    progress_callback,
                    download_id=download_id,
                    video_id=video_id,
                    real_itag=None,
                    retry_stage=1,
                )
                if retry_result.get('type') != 'error':
                    return retry_result
                retry_msg = retry_result.get('message') or ''
                if retry_msg:
                    msg = retry_msg

            # If quality-specific paths fail, retry once with yt-dlp automatic best selection.
            if retry_stage < 2 and (_is_format_unavailable_error(msg) or _is_auth_or_access_error(msg)):
                # If it looks like an auth/403 issue, attempt one cookie refresh before retrying
                if _is_auth_or_access_error(msg):
                    log.info('[Downloader] 403/Auth error detected. Refreshing cookies before retry...')
                    extract_cookies_to_file()

                progress_callback({'percent': '0%', 'speed': 'Retrying with universal compatibility mode', 'eta': ''})
                log.warning('[Downloader] Falling back to universal selector for %s (reason: %s)', url, msg)
                retry_result = download_video(
                    url,
                    '__auto_best__',
                    resolved_output,
                    progress_callback,
                    download_id=download_id,
                    video_id=video_id,
                    real_itag=None,
                    retry_stage=2,
                )
                if retry_result.get('type') != 'error':
                    return retry_result
                retry_msg = retry_result.get('message') or ''
                if retry_msg:
                    msg = retry_msg

            if _is_format_unavailable_error(msg):
                msg = (
                    'Selected quality is temporarily unavailable. FlashYT retried automatically; '
                    'please refresh qualities and try another option.'
                )
            return {'type': 'error', 'downloadId': download_id, 'videoId': video_id, 'message': msg}

        if not last_filename:
            # Fallback for rare cases where yt-dlp emits no Destination line.
            # Assume success if returncode is 0 and use videoId as basename.
            last_filename = f"{video_id}.mp4"
            log.warning('[Downloader] Success but filename not found. Using video_id as fallback: %s', last_filename)

        final_path = os.path.join(resolved_output, last_filename)
        with _active_lock:
            paused_jobs.pop(download_id, None)
        size_mb = round(os.path.getsize(final_path) / (1024 * 1024), 1) if os.path.exists(final_path) else 0
        return {
            'type': 'done',
            'downloadId': download_id,
            'videoId': video_id,
            'filename': last_filename,
            'path': final_path,
            'size_mb': size_mb,
            'actual_quality': actual_quality,
            'already_exists': already_exists,
        }
    finally:
        if process.poll() is None:
            _terminate_process_tree(process, timeout_s=1)
