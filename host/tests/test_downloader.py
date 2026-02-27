import pytest
import sys
import os

# Ensure the host directory is in the path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from downloader import _re_pct, _re_speed, _re_eta

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
