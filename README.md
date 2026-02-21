# One-Click YouTube Downloader (yt-dlp + Flask)

A seamless YouTube downloading experience integrated directly into your browser via Tampermonkey. It automatically bypasses YouTube bot protections and drops files directly into your `Downloads` folder using the fastest available quality (up to 1080p) combined with high-quality audio.

## 🌟 Key Features
1. **Multi-Tasking**: You can click download on 5 different YouTube videos at the same time. The server handles them all in parallel with independent UI progress tracking!
2. **One-Click Native App**: No Python required! You can download the pre-compiled `.exe` (Windows) or Linux binary, double click it, and the server runs silently in the background.
3. **Frontend (`userscript.js`)**: A Tampermonkey script securely injects a "Download" button directly into the YouTube player area.
4. **Backend (`server.py`)**: A lightweight Python server that receives the download command and uses `yt-dlp` + Deno JS solvers to bypass YouTube's restrictive bot-challenges.

---

## 🚀 1-Click Setup (For Friends & Non-Developers)

The easiest way to use this is to download the standalone app. You don't need to install Python!

1. Go to the [Releases Tab](../../releases/latest) on this GitHub repository.
2. Download the app for your system:
   - **Windows:** Download `youtube-downloader-windows.exe`
   - **Linux:** Download `youtube-downloader-linux`
3. Double-click to run the app. It will open a background terminal (do not close it).
4. *Important: You still need to have [FFmpeg](https://ffmpeg.org/download.html) installed on your system for audio/video merging!*

### Install the Browser Extension
1. Install the [Tampermonkey Extension](https://www.tampermonkey.net/) in your web browser.
2. Open the `userscript.js` file from this project, copy all of its text.
3. Click the Tampermonkey icon -> **Create a new script...**, paste the text, and click **File -> Save**.

---

## 💻 Developer Setup (Running from Python Source)

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
