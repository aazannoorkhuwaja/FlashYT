# FlashYT ⚡

> **Free & open-source YouTube video downloader — browser extension + native desktop app.**
> No cloud. No account. One click to download any video in full HD, 4K, or audio-only.

![FlashYT Icon](extension/icons/icon128.png)

---

## ✨ Features

- **One-click download** — button appears directly on YouTube video pages
- **Quality picker** — choose 360p → 4K UHD or Audio Only (MP3)
- **Live progress** — real-time speed, percentage, and ETA in the popup
- **Pause / Resume / Cancel** — full queue control
- **Auto-updates yt-dlp** — silently keeps itself working when YouTube changes their API
- **100% local** — your videos never leave your machine
- **Free & open source** — MIT License

---

## 🖥️ Supported Platforms & Browsers

| OS | Chrome | Brave | Edge | Chromium |
|---|---|---|---|---|
| Windows | ✅ | ✅ | ✅ | ✅ |
| macOS | ✅ | ✅ | ✅ | ✅ |
| Linux | ✅ | ✅ | ✅ | ✅ |

---

## 📦 Requirements

- **Python 3.8+** ([python.org](https://www.python.org/downloads/))
- **ffmpeg** — required for merging audio and video
  - Windows: [ffmpeg.org](https://ffmpeg.org/download.html) or `winget install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

---

## Quick Start (Installation)

### 🪟 Windows (Step-by-Step for Everyone)

> [!IMPORTANT]
> To avoid errors, please follow these **3 steps in order**. **Do not run the installer first.**

1.  **Step 1: Download & Extract Source Code (MANDATORY)**
    *   Click the green **Code** button at the top of this page and select **Download ZIP**.
    *   **Crucial**: Extract the ZIP file into a dedicated folder (like your Desktop).
    *   Open the extracted folder; you must see a folder named `extension` inside it.

2.  **Step 2: Load Extension from the `extension` Folder**
    *   Open Chrome, Brave, or Edge and go to `chrome://extensions`.
    *   Turn on **Developer Mode** (top right).
    *   Click **Load unpacked** and specifically select the `extension` folder you found in Step 1.
    *   _Once loaded, you should see the FlashYT icon. Keep this browser window open._

3.  **Step 3: Run the FlashYT Installer (.exe)**
    *   Now, download and run the [latest FlashYT-setup.exe](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).
    *   It will automatically detect your extension and link them together.
    *   If it asks for an "Extension ID", copy it from your browser's extensions page.

### 🍎 macOS & 🐧 Linux
1.  **Step 1**: Load the extension folder in your browser (Developer Mode).
2.  **Step 2**: Open your terminal and run:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
    ```

### Step 3 — Reload the Extension

After the installer finishes:
1. Go back to your extensions page (`chrome://extensions`)
2. Click the **🔄 refresh icon** on FlashYT
3. Open any YouTube video — the ⚡ Download button should appear!

---

## 🎬 How to Use

1. Go to any YouTube video: `https://www.youtube.com/watch?v=...`
2. Click the **⚡ Download** button next to the video actions
3. A quality picker appears — choose your resolution
4. Download starts immediately with a live progress bar
5. Open the FlashYT popup (click the extension icon) to see your queue

> [!IMPORTANT]
> **Sign in to YouTube in your browser before downloading.**
> FlashYT uses your browser's YouTube cookies to access video formats.
> Without being signed in, YouTube restricts which qualities are available and
> some videos may fail to download entirely. Just open YouTube, sign in once,
> and FlashYT will work automatically from that point on.

---

## 🔧 Troubleshooting

### "Host not connected" / popup shows "Disconnected"
The native host isn't running. Re-run the installer:
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
```
Then reload the extension (`chrome://extensions` → 🔄).

### "Failed to fetch qualities" or blank quality list
1. Make sure you're on a real YouTube watch page (`youtube.com/watch?v=...`)
2. Sign in to YouTube in the same browser profile
3. Right-click the ⚡ button → refresh qualities (the 🔄 icon in the modal)
4. If it persists, check the log file (see below)

### Download button doesn't appear on YouTube
1. Refresh the YouTube tab (Ctrl+R)
2. Make sure the extension is enabled on `chrome://extensions`
3. If YouTube recently changed their page layout, update FlashYT from [Releases](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)

### Windows SmartScreen warning on installer
This is normal for new/unsigned software. Click **"More info" → "Run anyway"**.
Always download only from the [official GitHub Releases page](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).

---

## 📋 Checking the Log (for debugging)

If something goes wrong, the log file has all the details:

| OS | Log location |
|---|---|
| Linux / macOS | `~/.config/YouTubeNativeExt/host.log` |
| Windows | `%APPDATA%\YouTubeNativeExt\host.log` |

**Quick command to tail the log:**
```bash
tail -f ~/.config/YouTubeNativeExt/host.log
```

When reporting a bug, always include the last 20 lines of this file.

---

## 🗑️ Uninstall

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/uninstall.sh | bash
```

Then go to `chrome://extensions` and remove FlashYT.

**Windows:** Use Windows Add/Remove Programs → uninstall FlashYT.

---

## 🐛 Reporting Bugs

Open an issue at [github.com/aazannoorkhuwaja/FlashYT/issues](https://github.com/aazannoorkhuwaja/FlashYT/issues)

Please include:
- Your OS, browser, and browser version
- FlashYT version (shown in popup → About tab)
- Exact steps to reproduce
- The last 20 lines of `host.log`

---

## 🤝 Contributing

PRs are welcome! If your change touches the host protocol or download queue states, run the test suite before submitting:
```bash
cd host
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

## 📄 License

MIT — free to use, share, and modify.

---

*Made with ❤️ by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
