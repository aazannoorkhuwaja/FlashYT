import subprocess
import threading
import os
import re
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
# Enable CORS for the Tampermonkey script
CORS(app)

# Global dictionary to store the status of downloads
# Key = job_id, Value = status dictionary
download_statuses = {}

# Set download path to user's standard Downloads directory
DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

# Pre-compile the ANSI escape code regex
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def run_download_thread(url, selected_format, job_id):
    """
    Runs yt-dlp in a separate background thread.
    Hooks are defined inside to capture the job_id closure.
    """
    # Track how many streams have finished downloading (video=1, audio=2)
    stream_finish_count = {"count": 0, "expected": 2 if "MP4" in selected_format else 1}

    def update_progress(d):
        """Hook function called by yt_dlp during the download process."""
        if job_id not in download_statuses:
            return

        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%')
            speed_str = d.get('_speed_str', '0MiB/s')

            # Clean up ANSI escape codes
            percent_str = ansi_escape.sub('', percent_str).strip()
            speed_str = ansi_escape.sub('', speed_str).strip()

            download_statuses[job_id] = {
                "status": "downloading",
                "percent": percent_str,
                "speed": speed_str,
                "filename": os.path.basename(d.get('filename', ''))
            }
        elif d['status'] == 'finished':
            stream_finish_count["count"] += 1

            if stream_finish_count["count"] >= stream_finish_count["expected"]:
                # All streams downloaded, FFmpeg will merge
                download_statuses[job_id] = {
                    "status": "processing",
                    "percent": "100%",
                    "speed": "-",
                    "filename": os.path.basename(d.get('filename', ''))
                }
            else:
                download_statuses[job_id] = {
                    "status": "downloading",
                    "percent": "50%",
                    "speed": "fetching audio...",
                    "filename": os.path.basename(d.get('filename', ''))
                }
        elif d['status'] == 'error':
            download_statuses[job_id] = {
                "status": "error",
                "error": "yt-dlp encountered an error during download."
            }

    def postprocessor_hook(d):
        """Hook called by yt-dlp when a postprocessor starts/finishes."""
        if d['status'] == 'started':
            download_statuses[job_id] = {
                "status": "processing",
                "percent": "100%",
                "speed": "merging...",
                "filename": ""
            }
        elif d['status'] == 'finished':
            download_statuses[job_id] = {
                "status": "finished",
                "percent": "100%",
                "speed": "-",
                "filename": os.path.basename(d.get('filename', ''))
            }

    outtmpl = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')

    ydl_opts = {
        'progress_hooks': [update_progress],
        'postprocessor_hooks': [postprocessor_hook],
        'outtmpl': outtmpl,
        'quiet': False,
        'no_warnings': False,
        'socket_timeout': 30,
        
        # Allow yt-dlp to download the JS Challenge Solver
        'remote_components': ['ejs:github'],

        # Use Chrome cookies to authenticate with YouTube
        'cookiesfrombrowser': ('brave',),

        # Network Resilience & Retry Logic
        'retries': float('inf'),
        'fragment_retries': float('inf'),
        'file_access_retries': float('inf'),
        'retry_sleep_functions': {'http': lambda n: 5},
        'continuedl': True,
    }

    if "MP4" in selected_format:
        # 1. Best video between 720p-1080p preferring smaller modern codecs (avc/hevc/vp9) + best audio
        # 2. Fallback to any best video <= 1080p + best audio
        # 3. Fallback to absolutely any video + audio or pre-merged file
        ydl_opts['format'] = (
            'bestvideo[height<=1080][height>=720][vcodec~="^((he|a)vc|vp9)"]+bestaudio/best/'
            'bestvideo[height<=1080]+bestaudio/best/'
            'bestvideo+bestaudio/best'
        )
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitleslangs'] = ['en', 'all']
        ydl_opts['embedsubtitles'] = True
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegEmbedSubtitle'
        }]
    elif "MP3" in selected_format:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Fallback if hooks don't fire for the final step
        if download_statuses.get(job_id, {}).get("status") != "finished":
            download_statuses[job_id] = {
                "status": "finished",
                "percent": "100%",
                "speed": "-",
                "filename": ""
            }
    except Exception as e:
        download_statuses[job_id] = {
            "status": "error",
            "error": str(e)
        }


@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    selected_format = "MP4"

    # Strip playlist parameters from URL so yt-dlp only downloads the single video
    # YouTube URLs like watch?v=xxx&list=yyy cause yt-dlp to download the entire playlist
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    # Keep only the video ID parameter, strip list/index/start_radio etc.
    clean_params = {k: v for k, v in params.items() if k in ('v',)}
    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
    url = urllib.parse.urlunparse(parsed._replace(query=clean_query))
    print(f"[Server] Sanitized URL: {url}")
    
    # Generate unique ID for this download
    job_id = str(uuid.uuid4())

    # Initialize the status
    download_statuses[job_id] = {
        "status": "starting",
        "percent": "0%",
        "speed": "0MiB/s"
    }

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    thread = threading.Thread(target=run_download_thread, args=(url, selected_format, job_id))
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Download started in background", "job_id": job_id}), 202


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    status = download_statuses.get(job_id, {"status": "idle"})
    return jsonify(status), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
