import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'host')))
import downloader


class TestDownloaderPaths(unittest.TestCase):
    """Tests for the two distinct download code paths in download_video()."""

    def _run_download(self, max_height, mock_lines=None):
        """
        Helper: runs download_video() with a mocked subprocess, captures
        the yt-dlp command that was actually built, and returns it.
        """
        if mock_lines is None:
            mock_lines = []

        mock_proc = MagicMock()
        mock_proc.stdout.__iter__ = MagicMock(return_value=iter(mock_lines))
        mock_proc.stdout.readline = MagicMock(side_effect=mock_lines + [''])
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0

        captured_cmd = []

        def fake_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return mock_proc

        with patch('downloader.get_ytdlp_path', return_value='/fake/yt-dlp'), \
             patch('downloader.get_ffmpeg_path', return_value='/fake/ffmpeg'), \
             patch('subprocess.Popen', side_effect=fake_popen):
            downloader.download_video(
                url='https://www.youtube.com/watch?v=test',
                max_height=max_height,
                output_dir='/tmp',
                progress_callback=lambda d: None
            )

        return captured_cmd

    # ------------------------------------------------------------------
    # Issue 10: Audio vs Video download path divergence
    # ------------------------------------------------------------------

    def test_audio_path_uses_extract_audio(self):
        """Asserts max_height='audio' builds command with --extract-audio and --audio-format mp3"""
        cmd = self._run_download(max_height='audio')
        self.assertIn('--extract-audio', cmd)
        self.assertIn('--audio-format', cmd)
        mp3_index = cmd.index('--audio-format') + 1
        self.assertEqual(cmd[mp3_index], 'mp3')
        # Must NOT contain a video format selector
        self.assertFalse(any('height<=' in arg for arg in cmd))

    def test_video_path_uses_height_selector(self):
        """Asserts a numeric max_height builds command with a height-based format selector"""
        cmd = self._run_download(max_height=1080)
        self.assertTrue(any('height<=1080' in arg for arg in cmd))
        self.assertNotIn('--extract-audio', cmd)

    def test_video_path_defaults_to_1080_on_bad_max_height(self):
        """Asserts a non-integer max_height (edge case) falls back to 1080p"""
        cmd = self._run_download(max_height='notanumber')
        self.assertTrue(any('height<=1080' in arg for arg in cmd))


class TestUpdateYtdlpErrors(unittest.TestCase):
    """Issue 12: Tests for network error handling in update_ytdlp()."""

    def test_update_returns_error_on_network_failure(self):
        """Asserts update_ytdlp() returns error when pip install fails on Linux/Mac"""
        import subprocess as sp
        with patch('subprocess.run',
                   side_effect=sp.CalledProcessError(1, 'pip')):
            result = downloader.update_ytdlp(lambda d: None)

        self.assertEqual(result.get('type'), 'error')

    def test_update_returns_error_on_timeout(self):
        """Asserts update_ytdlp() returns error on pip subprocess timeout"""
        import subprocess as sp
        with patch('subprocess.run',
                   side_effect=sp.TimeoutExpired('pip', 30)):
            result = downloader.update_ytdlp(lambda d: None)

        self.assertEqual(result.get('type'), 'error')


if __name__ == '__main__':
    unittest.main()
