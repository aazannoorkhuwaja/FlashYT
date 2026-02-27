import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import downloader


class DummyProc:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self.pid = 999999

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True
        self.terminated = True

    def poll(self):
        return 0 if self.terminated else None


def setup_function(_):
    downloader.active_processes.clear()
    downloader.paused_jobs.clear()


def test_pause_sets_stop_reason_and_terminates_process():
    proc = DummyProc()
    downloader.active_processes['dl_1'] = {
        'proc': proc,
        'stop_reason': None,
        'job_state': {
            'url': 'https://youtube.com/watch?v=abc123xyz00',
            'itag': 'video_720',
            'output_dir': '/tmp',
            'download_id': 'dl_1',
            'video_id': 'abc123xyz00',
            'real_itag': None,
        }
    }

    ok, msg = downloader.pause_video('dl_1')

    assert ok is True
    assert 'Pause' in msg or 'paused' in msg.lower()
    assert proc.terminated is True
    assert downloader.active_processes['dl_1']['stop_reason'] == 'paused'
    assert 'dl_1' not in downloader.paused_jobs


def test_resume_requeues_paused_job():
    downloader.paused_jobs['dl_2'] = {
        'url': 'https://youtube.com/watch?v=abc123xyz00',
        'itag': 'video_1080',
        'output_dir': '/tmp',
        'download_id': 'dl_2',
        'video_id': 'abc123xyz00',
        'real_itag': 137,
    }

    ok, payload, msg = downloader.resume_video('dl_2')

    assert ok is True
    assert payload['type'] == 'download'
    assert payload['downloadId'] == 'dl_2'
    assert payload['save_location'] == '/tmp'
    assert payload['resume'] is True
    assert 'dl_2' not in downloader.paused_jobs


def test_resume_while_pause_in_progress_reports_ok_without_payload():
    proc = DummyProc()
    downloader.active_processes['dl_4'] = {
        'proc': proc,
        'stop_reason': 'paused',
        'job_state': {
            'url': 'https://youtube.com/watch?v=abc123xyz00',
            'itag': 'video_720',
            'downloadId': 'dl_4',
            'videoId': 'abc123xyz00',
            'real_itag': None,
            'save_location': '/tmp',
        }
    }

    ok, payload, msg = downloader.resume_video('dl_4')

    assert ok is True
    assert payload is None
    assert 'queued' in msg.lower()


def test_cancel_clears_paused_job():
    downloader.paused_jobs['dl_3'] = {
        'url': 'x',
        'itag': 'video_360',
        'output_dir': '/tmp',
        'download_id': 'dl_3',
        'video_id': 'abc',
        'real_itag': None,
    }

    ok, msg = downloader.cancel_video('dl_3')

    assert ok is True
    assert 'dl_3' not in downloader.paused_jobs
