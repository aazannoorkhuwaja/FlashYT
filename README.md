# FlashYT ⚡

> **The most reliable free YouTube downloader — right in your browser.**
> No cloud. No account. No limits. One click and it's yours — in exactly the quality you chose.

![FlashYT Icon](extension/icons/icon128.png)

[![Version](https://img.shields.io/badge/version-2.1.6-brightgreen)](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## ✨ Why FlashYT?

FlashYT is built to **just work** — for everyone, on every machine, in every browser.

- **⚡ One-click download** — Download button appears directly on YouTube, no copy-pasting URLs
- **🎯 Exact quality every time** — Select 1080p, get exactly 1080p. Or 4K. Or 720p. Never a downgrade
- **✅ Quality badge** — Every completed download shows the actual resolution downloaded (e.g. `1080p`)
- **📊 Live progress** — Real-time speed, percentage, and ETA in the popup
- **⏸️ Full queue control** — Pause, Resume, Cancel at any time
- **🔄 Auto-healing** — Auto-refreshes cookies and retries if YouTube's API changes
- **🔁 Auto-updates yt-dlp** — Stays working even when YouTube changes their internals
- **🔒 100% local** — Videos stay on your machine. No servers. No tracking. No data collection
- **🆓 Free & open source** — MIT License

---

## 🖥️ Supported Platforms & Browsers

| OS | Chrome | Brave | Edge | Chromium |
|---|---|---|---|---|
| 🪟 Windows | ✅ | ✅ | ✅ | ✅ |
| 🍎 macOS | ✅ | ✅ | ✅ | ✅ |
| 🐧 Linux | ✅ | ✅ | ✅ | ✅ |

---

## 📦 Requirements

- **Python 3.8+** — [python.org](https://www.python.org/downloads/)
- **ffmpeg** — needed to merge audio and video streams for HD/4K
  - Windows: `winget install ffmpeg` or [ffmpeg.org](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

---

## 🚀 Quick Start — Fresh Install

### 🪟 Windows — 3 Steps (follow in order)

> [!IMPORTANT]
> Follow these 3 steps **in order**. Do not run the installer before loading the extension.

**Step 1 — Download & Extract the source code**
- Click the green **Code** button → **Download ZIP**
- Extract into a folder (e.g. your Desktop)
- Make sure the extracted folder contains an `extension` subfolder

**Step 2 — Load the extension**
- Open Chrome/Brave/Edge → go to `chrome://extensions`
- Enable **Developer Mode** (top-right toggle)
- Click **Load unpacked** → select the `extension` folder from Step 1
- The FlashYT icon should appear in your toolbar

**Step 3 — Run the installer**
- Download and run [FlashYT-setup.exe](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)
- It auto-detects your extension and links them. If it asks for an Extension ID, copy it from `chrome://extensions`
- After install: go to `chrome://extensions` → click **🔄 reload** on FlashYT

### 🍎 macOS & 🐧 Linux — 2 Steps

**Step 1 — Load the extension** (same as Windows Steps 1–2 above)

**Step 2 — Run the one-line installer:**
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
```

Then reload the extension: `chrome://extensions` → 🔄 on FlashYT.

---

## 🎬 How to Use

1. Open any YouTube video: `https://www.youtube.com/watch?v=...`
2. Click the red **⚡ Download** button that appears below the video
3. Pick your quality — **1080p**, **4K**, **audio only**, etc.
4. Download starts immediately. Watch progress live in the FlashYT popup
5. When done, a **`✓ 1080p`** quality badge confirms the exact resolution saved

> [!IMPORTANT]
> **Sign in to YouTube in your browser first.**
> FlashYT uses your browser's YouTube session cookies to access full HD and 4K streams.
> Without being signed in, YouTube restricts available qualities.
> Just open YouTube, sign in once, and FlashYT handles everything automatically from there.

---

## 🔄 How to Update

When a new version is released, the FlashYT popup will show a red "Update Available" banner. **Updating is a two-step process:** you must update both the native background engine AND the browser extension.

### Step 1: Update the Native Engine
Run the installation command for your system to fetch the latest background scripts:

**Linux & macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/scripts/update_windows.ps1 | iex
```
*(Note: Windows users can simply download and run the latest `.exe` installer from the Releases page instead).*

### Step 2: Update the Browser Extension
The `curl` command does not automatically update the extension inside your browser. To clear the "Update Available" banner:
1. Go to the [FlashYT Releases](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest) page and download the latest `Source code (zip)`.
2. Extract the zip file and **overwrite your old FlashYT folder** with the new files.
3. Open `chrome://extensions` (or `brave://extensions`).
4. Find the **FlashYT** card and click the **🔄 Reload icon**.
5. **Completely close and reopen your browser** to ensure the new background engine connects.

> [!CAUTION]
> **NEVER DELETE YOUR OLD EXTENSION FOLDER!** 
> If you delete the existing FlashYT folder instead of overwriting it, Chrome/Brave will generate a brand new internal Extension ID. The background host script is permanently locked to your original Extension ID. If the ID changes, your extension will say **"Disconnected"** entirely.
> **Only copy/paste the new files *inside* your existing folder to overwrite them.**

The red update banner will permanently disappear once the extension's version number matches the latest release!

---

## 🔧 Troubleshooting

### "Host not connected" / popup shows "Disconnected"
The native engine isn't running or installed correctly. Fix with:
```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/scripts/update_windows.ps1 | iex
```
Then reload the extension (`chrome://extensions` → 🔄).

### Download stuck at 0% or "Retrying with available quality"
This was a bug in older versions. **Update to v2.1.9** using the steps above. The newest engine handles YouTube's latest encryption changes and format selection flawlessly.

### Got 144p/360p instead of the quality I selected
Also fixed in **v2.1.9**. The format selector ensures you get exactly the high-bitrate resolution and file size shown in the picker.

### "Failed to fetch qualities" or blank quality list
1. Make sure you're on a real YouTube watch page (`youtube.com/watch?v=...`)
2. Sign in to YouTube in the same browser profile
3. Click the 🔄 refresh icon inside the quality picker modal
4. If it still fails, check the log (see below)

### Download button doesn't appear on YouTube
1. Refresh the YouTube tab (Ctrl+R)
2. Make sure FlashYT is enabled on `chrome://extensions`
3. If the button stopped appearing after a YouTube layout change, update FlashYT

### Windows SmartScreen warning on installer
Normal for unsigned software. Click **"More info" → "Run anyway"**.
Only download from [github.com/aazannoorkhuwaja/FlashYT/releases](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).

---

## 📋 Reading the Log (for debugging)

| OS | Log file path |
|---|---|
| Linux / macOS | `~/.config/YouTubeNativeExt/host.log` |
| Windows | `%APPDATA%\YouTubeNativeExt\host.log` |

```bash
# Live-view the log
tail -f ~/.config/YouTubeNativeExt/host.log
```

When reporting a bug, please include the last 20 lines of this file.

---

## 🗑️ Uninstall

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/uninstall.sh | bash
```
Then go to `chrome://extensions` and remove FlashYT.

**Windows:** Use Windows → Add/Remove Programs → uninstall FlashYT.

---

## 🐛 Reporting Bugs

Open an issue at [github.com/aazannoorkhuwaja/FlashYT/issues](https://github.com/aazannoorkhuwaja/FlashYT/issues)

Please include:
- Your OS, browser, and version
- FlashYT version (popup → **About** tab)
- Steps to reproduce the issue
- Last 20 lines of `host.log`

---

## 🤝 Contributing

PRs are welcome! Run the test suite before submitting:
```bash
cd host
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

## 📄 License

MIT — free to use, share, and modify.

---

*Vibe Coded by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
