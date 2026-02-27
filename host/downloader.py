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

from cookies import detect_browser, get_best_available_cookies
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
        return sys_path
    if sys.platform == 'win32':
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        return os.path.join(base_dir, 'yt-dlp.exe')
    return '/usr/local/bin/yt-dlp' if os.path.exists('/usr/local/bin/yt-dlp') else '/usr/bin/yt-dlp'


def get_ffmpeg_path():
    sys_path = shutil.which('ffmpeg')
    if sys_path:
        return sys_path
    if sys.platform == 'win32':
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        return os.path.join(base_dir, 'ffmpeg.exe')
    return '/usr/local/bin/ffmpeg' if os.path.exists('/usr/local/bin/ffmpeg') else '/usr/bin/ffmpeg'


def _build_video_format_string(max_height):
    try:
        h = int(max_height)
    except (TypeError, ValueError):
        h = 1080
    return (
        f"bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/"
        "bestvideo+bestaudio/best/bestvideo/bestaudio"
    )


def _resolve_output_dir(path_hint):
    target = path_hint or os.path.join(os.path.expanduser('~'), 'Downloads')
    target = os.path.abspath(os.path.expanduser(target))
    os.makedirs(target, exist_ok=True)
    return target


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


def prefetch_qualities(url):
    hint = 'If this persists, sign in to YouTube in your browser and restart FlashYT.'

    def with_hint(msg):
        msg = (msg or '').strip()
        if hint in msg:
            return msg
        return f'{msg} {hint}'.strip()

    fast_result = _prefetch_with_timeout(url, timeout_s=8)
    if fast_result and not fast_result.get('error') and fast_result.get('qualities'):
        return fast_result

    fallback = _prefetch_with_ytdlp(url, timeout_s=25)
    if fallback and not fallback.get('error') and fallback.get('qualities'):
        return fallback

    if fallback and fallback.get('error'):
        return {'error': with_hint(fallback['error'])}
    if fast_result and fast_result.get('error'):
        return {'error': with_hint(fast_result['error'])}
    return {'error': with_hint('Failed to prefetch qualities.')}


def _build_download_cmd(url, itag, output_dir, download_id, real_itag):
    cmd = [
        get_ytdlp_path(),
        '--no-playlist',
        '--ffmpeg-location', get_ffmpeg_path(),
        '--ignore-config',
        '--newline',
        '--no-warnings',
        '--no-update',
        '--no-check-certificate',
        '--continue',
        '--part',
        '--progress',
        '--cache-dir', os.path.join(os.path.expanduser('~'), '.flashyt_cache', download_id or 'default'),
        '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
    ]
    if shutil.which('aria2c'):
        cmd.extend([
            '--downloader', 'aria2c',
            '--downloader-args', 'aria2c:-c -x 16 -s 16 -k 1M --summary-interval=1 --console-log-level=notice',
        ])

    cookie_opts = get_best_available_cookies()
    if 'cookiefile' in cookie_opts:
        cmd.extend(['--cookies', cookie_opts['cookiefile']])

    if real_itag and real_itag != 'audio_only':
        cmd.extend([
            '-f', f'{real_itag}+bestaudio[ext=m4a]/bestaudio',
            '--merge-output-format', 'mp4',
            '--write-subs', '--sub-langs', 'en,all', '--embed-subs',
        ])
    elif isinstance(itag, str) and itag.startswith('video_'):
        try:
            h = int(itag.split('_')[1])
        except Exception:
            h = 1080
        cmd.extend([
            '-f', _build_video_format_string(h),
            '--merge-output-format', 'mp4',
            '--write-subs', '--sub-langs', 'en,all', '--embed-subs',
        ])
    elif itag == 'audio_only':
        if real_itag:
            cmd.extend(['-f', str(real_itag), '--extract-audio', '--audio-format', 'mp3'])
        else:
            cmd.extend(['-f', 'bestaudio/best', '--extract-audio', '--audio-format', 'mp3'])

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


def download_video(url, itag, output_dir, progress_callback, download_id=None, video_id=None, real_itag=None):
    if not url or not itag:
        return {'type': 'error', 'downloadId': download_id, 'videoId': video_id, 'message': 'Missing URL or format.'}

    download_id = download_id or f'dl_{int(time.time() * 1000)}'
    resolved_output = _resolve_output_dir(output_dir)

    cmd = _build_download_cmd(url, itag, resolved_output, download_id, real_itag)
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
    already_exists = False
    last_progress = [time.time()]
    log_tail = deque(maxlen=200)

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
            msg = 'yt-dlp encountered an error.'
            for err_line in reversed(log_tail):
                if 'ERROR:' in err_line:
                    msg = err_line.split('ERROR:', 1)[1].strip()
                    break
                if err_line.lower().startswith('error:'):
                    msg = err_line.split(':', 1)[1].strip()
                    break
            return {'type': 'error', 'downloadId': download_id, 'videoId': video_id, 'message': msg}

        if not last_filename:
            return {
                'type': 'error',
                'downloadId': download_id,
                'videoId': video_id,
                'message': 'Finished, but output filename could not be determined.',
            }

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
            'already_exists': already_exists,
        }
    finally:
        if process.poll() is None:
            _terminate_process_tree(process, timeout_s=1)
