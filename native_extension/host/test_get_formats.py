import yt_dlp
import copy

CACHED = {}

def get_formats(url):
    ydl_opts = {'skip_download': True, 'quiet': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        CACHED[url] = info
        print("Extracted formats!")

def download_video(url, format_str):
    ydl_opts = {
        'format': format_str,
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'noprogress': True,
        'quiet': True,
        'noplaylist': True,
    }
    print("Downloading with cache...")
    if url in CACHED:
        info = copy.deepcopy(CACHED[url])
        info['format'] = format_str
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.process_ie_result(info, download=True)
        print("Done via cache!")

url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
get_formats(url)
download_video(url, "bestvideo[height<=144]+bestaudio/best")
