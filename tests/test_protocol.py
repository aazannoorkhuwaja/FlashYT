import sys
import json
import struct
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

# Prepend host path to access modules
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

    def test_protocol_read_message(self):
        """Asserts host.py correctly unpacks Chrome's little-endian 32-bit JSON payload"""
        test_msg = {"type": "ping", "data": "hello"}
        raw_stream = self.build_chrome_message(test_msg)
        
        # Mock sys.stdin.buffer with our simulated Chrome byte stream
        with patch('sys.stdin.buffer.read') as mock_read:
            # We mock the sequence of `read(4)` then `read(length)`
            mock_read.side_effect = [raw_stream[:4], raw_stream[4:]]
            
            result = host.read_message()
            self.assertEqual(result, test_msg)
            self.assertEqual(result.get("type"), "ping")

    def test_protocol_send_message(self):
        """Asserts host.py correctly packs a response back to Chrome"""
        test_msg = {"type": "pong", "version": "1.0"}
        
        # We need to capture the raw binary stdout buffer using .write side-effect
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

if __name__ == '__main__':
    unittest.main()
