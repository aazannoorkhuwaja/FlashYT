# ⚡ FlashYT — One-Click YouTube Downloader (v2.2.5)

> **Download YouTube videos in any quality, directly from your browser. No accounts. No cloud. Completely free.**

![FlashYT Icon](https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/extension/icons/icon128.png)

[![Version](https://img.shields.io/github/v/release/aazannoorkhuwaja/FlashYT?label=version&color=brightgreen)](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## ✨ What does it do?

FlashYT puts a **⚡ Download button** right under every YouTube video. Pick your quality, click download. That's it.

- **⚡ One-click** — Download button appears right on YouTube
- **🎯 Up to 4K/8K** — Get exactly the quality you choose
- **📊 Live progress** — See speed, percent, and time left
- **🔒 100% private** — Videos go straight to your computer
- **🆓 Free forever** — No subscriptions, no accounts

---

## 🎬 See It in Action

![FlashYT Demo](docs/images/flashyt_demo.gif)

---

## 🪟 Windows — How to Install

### 📥 1. Install the Native Host
1. Go to the **[Releases page](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)** and download **`FlashYT-setup.exe`**
2. Double-click it. If Windows shows a blue warning → click **"More info"** → **"Run anyway"** *(safe to do)*
3. Click **Next** through the installer until finished.

### 🧩 2. Load the Extension
Modern browsers block silent extension installations for security reasons, so you must load it manually:
1. Open your browser's extensions page:
   - Chrome: **`chrome://extensions`**
   - Brave: **`brave://extensions`**
   - Edge: **`edge://extensions`**
2. Turn ON **"Developer mode"** (usually a toggle in the top-right corner)
3. Click **"Load unpacked"**
4. Navigate to this exact folder and select it:
   ```
   C:\Users\YourName\AppData\Local\Programs\FlashYT\extension
   ```
   *(Hint: Replace `YourName` with your Windows username. To find it quickly: press `Win + R`, type `%localappdata%\Programs\FlashYT\extension`, and copy the folder path!)*
5. **Open any YouTube video and click the ⚡ Download button!**

---

## 🍎 macOS — How to Install

### ✅ Method 1 — One Command *(Easiest — try this first)*

1. Open **Safari or Chrome** and go to `chrome://extensions`
2. Turn on **"Developer mode"** (toggle top-right)
3. Click **"Load unpacked"** → Select the `extension` folder from the [downloaded ZIP](https://github.com/aazannoorkhuwaja/FlashYT/archive/refs/heads/main.zip)
4. Open **Terminal** (press `Cmd + Space`, type `Terminal`, press Enter)
5. Paste this and press Enter:
   ```bash
   curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh && chmod +x install.sh && bash install.sh
   ```
6. When done, go back to `chrome://extensions` and click the **🔄 reload icon** on FlashYT
7. Open YouTube — the ⚡ button is there!

> **Didn't work? 👇 Try Method 2**

---

### 🔄 Method 2 — Step by Step *(if the one-liner failed)*

1. **Download** the [FlashYT ZIP](https://github.com/aazannoorkhuwaja/FlashYT/archive/refs/heads/main.zip) and unzip it (double-click the ZIP file)
2. **Load the extension:**
   - In Chrome/Brave/Edge go to `chrome://extensions`
   - Enable **Developer mode**
   - Click **Load unpacked** → select the `extension` folder inside the unzipped folder
3. **Run the helper script** — open Terminal and paste these one by one:
   ```bash
   curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh
   chmod +x install.sh
   bash install.sh
   ```
4. **Reload the extension** at `chrome://extensions` (click the 🔄 icon on FlashYT)
5. Open any YouTube page — done!

> **Still stuck? 👇 See Troubleshooting below**

---

## 🐧 Linux — How to Install

### ✅ Method 1 — One Command *(Easiest — try this first)*

Open **Terminal** and paste this single line:
```bash
curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh && chmod +x install.sh && bash install.sh
```
Then follow the on-screen instructions. When done, load the extension (the script will tell you how).

> **Didn't work? 👇 Try Method 2**

---

### 🔄 Method 2 — Manual Step by Step *(if the one-liner failed)*

1. **Download the ZIP:**
   ```bash
   curl -L -o FlashYT.zip https://github.com/aazannoorkhuwaja/FlashYT/archive/refs/heads/main.zip
   unzip FlashYT.zip
   cd FlashYT-main
   ```

2. **Load the extension:**
   - Open Chrome/Brave/Edge, go to `chrome://extensions`
   - Enable **Developer mode** (toggle top-right)
   - Click **Load unpacked** → select the `extension` folder

3. **Run the setup script:**
   ```bash
   chmod +x install.sh
   bash install.sh
   ```

4. **Reload the extension** at `chrome://extensions` (🔄 icon on FlashYT)

5. Open YouTube — the ⚡ button will appear!

> **Still stuck? 👇 See Troubleshooting below**

---

### 🔄 Method 3 — Manual Setup Without Script *(if both above failed)*

If `curl` or the script isn't available on your system:

1. Install `yt-dlp` and `ffmpeg` manually:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   pip3 install yt-dlp

   # Arch
   sudo pacman -S yt-dlp ffmpeg

   # Fedora
   sudo dnf install yt-dlp ffmpeg
   ```
2. Run the host setup directly:
   ```bash
   cd FlashYT-main/host
   pip3 install -r requirements.txt
   python3 setup.sh   # or: bash host/setup.sh from the root folder
   ```
3. Load the extension in your browser as in Method 2 step 2

---
 
 ## 🔄 Updating FlashYT (v2.2.5+)
 
 To get the latest 4K fixes and signature bypasses, you must update both parts:
 
 ### 1. Update the Host
 - **Windows**: Download and run the new **[FlashYT-setup.exe](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)**. It will overwrite your old version automatically.
 - **Mac/Linux**: Re-run the one-line install command from the installation sections above.
 
 ### 2. Update the Extension
 Since FlashYT is loaded manually, it does not auto-update:
 1. Download the new [source code ZIP](https://github.com/aazannoorkhuwaja/FlashYT/archive/refs/heads/main.zip).
 2. Replace your old `extension` folder with the new one.
 3. Go to `chrome://extensions` and click the **🔄 Reload** icon on the FlashYT card.
 
 ---
 
 ## 🔧 Troubleshooting — Quick Fixes

| Problem | Fix |
|---|---|
| **"Host not connected"** in extension | Re-run the installer (Windows) or `bash install.sh` (Mac/Linux), then reload the extension |
| **Extension doesn't appear** in browser | Go to `chrome://extensions` → Enable Developer mode → Load unpacked → select `...AppData\Local\Programs\FlashYT\extension` |
| **Download stuck at 0%** | YouTube API changed — re-run `install.sh` or reinstall to get the latest yt-dlp version |
| **Button not showing** after extension loaded | Hard-refresh the YouTube page: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac) |
| **AV / antivirus blocking** | Temporarily disable antivirus, reinstall, then add FlashYT to AV exceptions |

### 📋 Check the Logs

If something's still wrong, look at the log file for error details:
- **Windows:** `%APPDATA%\YouTubeNativeExt\host.log`
- **Mac/Linux:** `~/.config/YouTubeNativeExt/host.log`

### 💬 Still stuck?

[Open an issue on GitHub](https://github.com/aazannoorkhuwaja/FlashYT/issues) — paste the log contents and we'll help you out!

---

## ⚙️ Optional Settings

FlashYT works out of the box, but you can tweak it with a `.env` file. Copy `.env.example` and rename it `.env`:
- `FLASHYT_MAX_CONCURRENT` — how many downloads run at once (default: 3)
- `FLASHYT_INNERTUBE_KEY` — your own InnerTube key for faster quality detection

---

## 📄 License

MIT — free to use, modify, and share. See [LICENSE](LICENSE).

---

*Vibe Coded by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
