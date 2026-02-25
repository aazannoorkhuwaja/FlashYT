import sys
import json
import struct
import unittest
from unittest.mock import patch, MagicMock

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'host')))

import host

class TestChromeNativeMessagingProtocol(unittest.TestCase):

    def build_chrome_message(self, msg_dict):
        """Simulates Chrome packing a JSON dictionary into a Little-Endian unsigned int pipe"""
        encoded_json = json.dumps(msg_dict).encode('utf-8')
        length_prefix = struct.pack('<I', len(encoded_json))
        return length_prefix + encoded_json

    def unpack_python_response(self, raw_bytes):
        """Unpacks the response Python sent back to Chrome"""
        if len(raw_bytes) < 4:
            return None
        msg_length = struct.unpack('<I', raw_bytes[:4])[0]
        msg_str = raw_bytes[4:4+msg_length].decode('utf-8')
        return json.loads(msg_str)

    # ------------------------------------------------------------------
    # Core IPC Protocol Tests
    # ------------------------------------------------------------------

    def test_protocol_read_message(self):
        """Asserts host.py correctly unpacks Chrome's little-endian 32-bit JSON payload"""
        test_msg = {"type": "ping", "data": "hello"}
        raw_stream = self.build_chrome_message(test_msg)

        with patch('sys.stdin.buffer.read') as mock_read:
            mock_read.side_effect = [raw_stream[:4], raw_stream[4:]]
            result = host.read_message()
            self.assertEqual(result, test_msg)
            self.assertEqual(result.get("type"), "ping")

    def test_protocol_send_message(self):
        """Asserts host.py correctly packs a response back to Chrome"""
        test_msg = {"type": "pong", "version": "1.0"}

        captured_bytes = bytearray()
        def mock_write(b):
            captured_bytes.extend(b)
            return len(b)

        with patch('sys.stdout.buffer.write', side_effect=mock_write):
            host.send_message(test_msg)

            output_bytes = bytes(captured_bytes)
            decoded_msg = self.unpack_python_response(output_bytes)

            self.assertEqual(decoded_msg, test_msg)
            self.assertEqual(decoded_msg.get("type"), "pong")

    def test_protocol_read_empty_pipe(self):
        """Asserts host.py handles a dead or closing pipe without crashing"""
        with patch('sys.stdin.buffer.read', return_value=b''):
            result = host.read_message()
            self.assertIsNone(result)

    # ------------------------------------------------------------------
    # Architecture Fix Tests (Issue 1, 3)
    # ------------------------------------------------------------------

    def test_dev_mode_accepts_plain_json(self):
        """Asserts --dev-mode path reads raw JSON without a 4-byte prefix"""
        test_msg = {"type": "ping", "dev": True}
        raw_json = json.dumps(test_msg).encode('utf-8')

        with patch('sys.stdin.buffer.read') as mock_read:
            # Simulate: first read(4) returns the first 4 bytes of JSON string
            # then read() returns the rest
            mock_read.side_effect = [raw_json[:4], raw_json[4:]]
            result = host.read_message(dev_mode=True)
            self.assertEqual(result, test_msg)

    def test_send_message_blocked_when_host_not_alive(self):
        """Asserts send_message returns False silently when _host_alive is False"""
        original = host._host_alive
        try:
            host._host_alive = False
            result = host.send_message({"type": "test"})
            self.assertFalse(result)
        finally:
            host._host_alive = original  # Restore global state

    def test_send_message_handles_broken_pipe(self):
        """Asserts send_message catches BrokenPipeError and returns False gracefully"""
        host._host_alive = True
        with patch('sys.stdout.buffer.write', side_effect=BrokenPipeError("pipe closed")):
            result = host.send_message({"type": "test"})
            self.assertFalse(result)

    # ------------------------------------------------------------------
    # Code Quality Fix Tests (Issue 5 — _find_executable DRY helper)
    # ------------------------------------------------------------------

    def test_find_executable_raises_when_not_found(self):
        """Asserts _find_executable raises FileNotFoundError with a clear message when binary is absent"""
        import downloader
        with patch('os.path.exists', return_value=False), \
             patch('shutil.which', return_value=None), \
             patch('sys.frozen', False, create=True):
            with self.assertRaises(FileNotFoundError) as ctx:
                downloader._find_executable('nonexistent-tool')
            self.assertIn('nonexistent-tool', str(ctx.exception))

    def test_find_executable_prefers_appdata_override(self):
        """Asserts _find_executable returns the AppData path over any bundled version"""
        import downloader
        fake_appdata_path = '/fake/appdata/YouTubeNativeExt/yt-dlp'

        def fake_exists(path):
            return path == fake_appdata_path

        with patch('os.path.exists', side_effect=fake_exists), \
             patch('os.environ.get', return_value='/fake/appdata'), \
             patch('platform.system', return_value='Linux'):
            result = downloader._find_executable('yt-dlp')
            self.assertEqual(result, fake_appdata_path)


    # ------------------------------------------------------------------
    # Issue 9: URL Validation tests
    # ------------------------------------------------------------------

    def test_valid_youtube_url_passes_validation(self):
        """Asserts a standard youtube.com URL is accepted by handle_task"""
        sent = []
        with patch.object(host, 'send_message', side_effect=lambda m: sent.append(m)), \
             patch.object(host, 'prefetch_qualities', return_value={"type": "prefetch_result", "qualities": []}), \
             patch.object(host, 'downloads_dir', '/tmp', create=True):
            host.handle_task({"type": "prefetch", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        # Should NOT have sent an error
        self.assertFalse(any(m.get("message") == "Invalid YouTube URL." for m in sent))

    def test_youtu_be_short_url_passes_validation(self):
        """Asserts a youtu.be short URL is accepted by handle_task"""
        sent = []
        with patch.object(host, 'send_message', side_effect=lambda m: sent.append(m)), \
             patch.object(host, 'prefetch_qualities', return_value={"type": "prefetch_result", "qualities": []}), \
             patch.object(host, 'downloads_dir', '/tmp', create=True):
            host.handle_task({"type": "prefetch", "url": "https://youtu.be/dQw4w9WgXcQ"})
        self.assertFalse(any(m.get("message") == "Invalid YouTube URL." for m in sent))

    def test_non_youtube_url_is_rejected(self):
        """Asserts a non-YouTube URL is rejected with a clear error message"""
        sent = []
        with patch.object(host, 'send_message', side_effect=lambda m: sent.append(m)):
            host.handle_task({"type": "prefetch", "url": "https://vimeo.com/123456"})
        self.assertTrue(any(m.get("message") == "Invalid YouTube URL." for m in sent))

