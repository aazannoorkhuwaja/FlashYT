import sys
import os
import unittest
from unittest.mock import patch, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import detect_extension_id

class TestDetectExtensionId(unittest.TestCase):

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isdir')
    @patch('builtins.open', new_callable=mock_open, read_data='{"name": "YouTube Native Downloader"}')
    def test_finds_packed_extension(self, mock_file, mock_isdir, mock_listdir, mock_exists):
        # Simulate exist checks passing for the Extension directory
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        # Simulate finding a 32-character extension ID and a version directory inside
        fake_ext_id = "a" * 32
        mock_listdir.side_effect = [
            [fake_ext_id, "short", "invalid"], # Contents of Extensions dir
            ["1.0.0_0"]                        # Contents of the specific extension dir
        ]

        ext_id = detect_extension_id.find_extension_id()
        self.assertEqual(ext_id, fake_ext_id)

    @patch('os.path.exists', return_value=False)
    def test_returns_none_when_no_profiles_found(self, mock_exists):
        ext_id = detect_extension_id.find_extension_id()
        self.assertIsNone(ext_id)

if __name__ == '__main__':
    unittest.main()
