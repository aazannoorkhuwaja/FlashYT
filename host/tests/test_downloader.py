import pytest
import sys
import os

# Ensure the host directory is in the path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import downloader
from downloader import (
    _build_download_cmd,
    _is_auth_or_access_error,
    _is_format_unavailable_error,
    _re_eta,
    _re_pct,
    _re_speed,
)

def test_yt_dlp_standard_progress():
    line = "[download]  14.5% of ~3.50MiB at    1.50MiB/s ETA 00:02"
    assert _re_pct.search(line).group(1) == "14.5%"
    assert _re_speed.search(line).group(1) == "1.50MiB/s"
    assert _re_eta.search(line).group(1) == "00:02"

def test_yt_dlp_kib_progress():
    line = "[download]   1.4% of 15.68MiB at   50.60KiB/s ETA 05:12"
    assert _re_pct.search(line).group(1) == "1.4%"
    assert _re_speed.search(line).group(1) == "50.60KiB/s"
    assert _re_eta.search(line).group(1) == "05:12"

def test_yt_dlp_completion_format():
    # Edge case: When yt-dlp finishes, it prints "in HH:MM:SS at SPEED" instead of ETA
    line = "[download] 100% of  54.66MiB in 00:00:13 at 4.09MiB/s"
    assert _re_pct.search(line).group(1) == "100%"
    assert _re_speed.search(line).group(1) == "4.09MiB/s"
    assert _re_eta.search(line) is None

def test_yt_dlp_ignored_lines():
    # Expected to explicitly fail matching so it skips cleanly
    line_merger = "[Merger] Merging formats into \"video.mp4\""
    assert _re_pct.search(line_merger) is None

    line_extract = "[ExtractAudio] Destination: audio.mp3"
    assert _re_speed.search(line_extract) is None


def test_format_unavailable_error_detection():
    assert _is_format_unavailable_error("Requested format is not available.") is True
    assert _is_format_unavailable_error("No video formats found!") is True
    assert _is_format_unavailable_error("Sign in to confirm you are not a bot") is False


def test_auth_or_access_error_detection():
    assert _is_auth_or_access_error("Sign in to confirm you're not a bot") is True
    assert _is_auth_or_access_error("HTTP Error 403: Forbidden") is True
    assert _is_auth_or_access_error("Requested format is not available.") is False


def test_build_cmd_audio_only_uses_audio_selector():
    cmd = _build_download_cmd(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "audio_only",
        "/tmp",
        "dl_test_audio",
        140,
    )
    assert "-f" in cmd
    selector = cmd[cmd.index("-f") + 1]
    assert selector == "bestaudio[ext=m4a]/bestaudio/best"
    assert "--extract-audio" in cmd


def test_build_cmd_real_itag_has_adaptive_fallback_selector():
    cmd = _build_download_cmd(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_720",
        "/tmp",
        "dl_test_video",
        137,
    )
    selector = cmd[cmd.index("-f") + 1]
    # With real_itag removed, the selector is pure height-based — no stale token prefix
    assert "height<=720" in selector
    assert not selector.startswith("137")


def test_build_cmd_does_not_force_subtitle_flags():
    cmd = _build_download_cmd(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_720",
        "/tmp",
        "dl_no_subs",
        None,
    )
    assert "--write-subs" not in cmd
    assert "--embed-subs" not in cmd
