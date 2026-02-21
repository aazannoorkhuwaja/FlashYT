# One-Click YouTube Downloader (yt-dlp + Flask)

A seamless YouTube and YouTube Playlist downloading experience integrated directly into your browser via Tampermonkey. It automatically bypasses YouTube bot protections and drops files directly into your `Downloads` folder using the fastest available quality (up to 1080p) combined with high-quality audio.

## How it works
1. **Frontend (`userscript.js`)**: A Tampermonkey script securely injects a "Download" button directly into the YouTube player area (next to Subscribe/Like buttons).
2. **Backend (`server.py`)**: A lightweight Python Flask server runs quietly in the background on your PC. It receives the download command and uses `yt-dlp` to download the video bypassing bot-challenges using JS solvers.
3. **Progress Tracking**: You can click download on multiple videos at once. The button tracks the live download and merging progress directly on your YouTube screen.

---

## 🚀 Setup Instructions

### Step 1: Install Dependencies
You need Python & [FFmpeg](https://ffmpeg.org/) installed on your computer.

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg python3 python3-pip python3-venv

# Clone this repository
git clone https://github.com/aazan-noor-khuwaja/one_click_ytmp4_download.git
cd one_click_ytmp4_download
```

### Step 2: Setup Python Backend
Create a virtual environment and install the required Python packages (`yt-dlp`, `flask`, `flask-cors`):

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install the exact requirements 
pip install yt-dlp flask flask-cors secretstorage
```

> **Note on Browser Cookies:** The script is currently configured to use `brave` browser cookies to bypass age-restrictions and premium video locks. If you use Chrome instead, edit `server.py` and change `'cookiesfrombrowser': ('brave',)` to `'cookiesfrombrowser': ('chrome',)`.

### Step 3: Start the Background Server
Run the Flask server. It will listen on `localhost:5000` to receive download commands.

```bash
python3 server.py
# Leave this terminal running in the background while you use YouTube
```

### Step 4: Install the Tampermonkey Userscript
1. Install the [Tampermonkey Extension](https://www.tampermonkey.net/) in your web browser.
2. Click the Tampermonkey icon -> **Create a new script...**
3. Open the `userscript.js` file from this project, copy all of its contents, and paste it into the Tampermonkey editor.
4. Click **File -> Save**.

### Step 5: Test it out!
1. Go to any YouTube video (refresh the page if it's already open).
2. You will see a red `Download` button right underneath the video.
3. Click it! The button will update to show you the progress (e.g. `Downloading 45%` -> `Merging...` -> `Complete!`).
4. Find the high-quality MP4 file in your computer's `~/Downloads` folder!
