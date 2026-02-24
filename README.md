# One-Click YouTube Downloader 🚀

## 🛠️ Installation Guide

Follow these simple steps to install the extension and backend on your machine.

### Step 1: Install the Browser Extension
1. Download the newest `One-Click-Youtube-Downloader-Native.zip` from the [Releases](https://github.com/aazannoorkhuwaja/one_click_ytmp4_download/releases) page and extract it.
2. Open Chrome or Brave and navigate to `chrome://extensions`.
3. Toggle **Developer mode** ON (top right corner).
4. Click **Load unpacked** and select the extracted `extension` folder.
5. The extension will appear. **Copy its 32-character ID string** (e.g., `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`). You need this for Step 2.

### Step 2: Install the Native Backend
The browser extension needs permission to talk to the Python download motor (`yt-dlp`). You only need to do this once.

1. Open the extracted folder and go inside the `host` directory.
2. Run the automatic setup script for your OS:
   *   **Windows:** Double-click `setup_windows.bat`
   *   **Mac / Linux:** Open terminal and run `./setup_mac_linux.sh`
3. The script will open a terminal window automatically creating a virtual environment and installing `yt-dlp`. 
4. When prompted, **paste the 32-character Extension ID** you copied from the browser in Step 1.

### Step 3: Download!
That's it! 
1. Open any YouTube video.
2. A red **Download** button will appear securely next to the channel owner's name.
3. Click it to instantly reveal quality sizes (e.g., 1080p - 45.2MB).
4. Select a quality. Your video will immediately begin downloading straight to your system's `Downloads` folder!

---

## 💻 Tech Stack
*   **Frontend**: Vanilla JavaScript Chrome/Brave Extension (Manifest V3)
*   **Backend**: Python 3 Native Messaging Host
*   **Extraction Engine**: `yt-dlp`

> Built and constantly iterated by **Aazan Noor Khuwaja**.
