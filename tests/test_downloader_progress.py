import unittest
import re

# We will test the exact regexes from downloader.py
progress_regex = re.compile(r'\[download\][^\d]*([\d.]+)%')
speed_regex = re.compile(r'at\s+([~]?[\d.]+[A-Za-z]+/s)')
eta_regex = re.compile(r'ETA\s+([\d:]+)')

class TestDownloaderParsing(unittest.TestCase):

    def extract(self, line):
        prog_match = progress_regex.search(line)
        speed_match = speed_regex.search(line)
        eta_match = eta_regex.search(line)

        return {
            "percent": f"{prog_match.group(1)}%" if prog_match else None,
            "speed": speed_match.group(1) if speed_match else None,
            "eta": eta_match.group(1) if eta_match else None
        }

    def test_standard_yt_dlp_output(self):
        line = "[download]  14.5% of   20.10MiB at    3.45MiB/s ETA 00:04"
        res = self.extract(line)
        self.assertEqual(res["percent"], "14.5%")
        self.assertEqual(res["speed"], "3.45MiB/s")
        self.assertEqual(res["eta"], "00:04")

    def test_slow_speed_output(self):
        line = "[download]   0.1% of  150.00MiB at   50.00KiB/s ETA 12:34"
        res = self.extract(line)
        self.assertEqual(res["percent"], "0.1%")
        self.assertEqual(res["speed"], "50.00KiB/s")
        self.assertEqual(res["eta"], "12:34")

    def test_missing_eta_or_speed_but_valid_progress(self):
        line = "[download]  99.9% of Unknown size"
        res = self.extract(line)
        self.assertEqual(res["percent"], "99.9%")
        self.assertIsNone(res["speed"])
        self.assertIsNone(res["eta"])

    def test_100_percent(self):
        line = "[download] 100.0% of   20.10MiB at    4.20MiB/s ETA 00:00"
        res = self.extract(line)
        self.assertEqual(res["percent"], "100.0%")

if __name__ == '__main__':
    unittest.main()
