import yt_dlp

def download_video(url, format_str):
    ydl_opts = {
        'format': format_str,
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'noprogress': True,
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print("Downloaded!")

url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
download_video(url, "bestvideo[height<=144]+bestaudio/best")
