# FlashYT ⚡

> **The easiest, most reliable free YouTube downloader — right in your browser.**
> No cloud. No accounts. No limits. One click and it's yours — in exactly the quality you want.

![FlashYT Icon](extension/icons/icon128.png)

[![Version](https://img.shields.io/badge/version-2.1.9-brightgreen)](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## ✨ Why FlashYT?

FlashYT is built to **just work** — for everyone, on every computer, in every browser.

- **⚡ One-click download** — A friendly Download button appears directly under YouTube videos! No copying and pasting links.
- **🎯 Exact quality over promises** — If you select 1080p, you get exactly 1080p.
- **✅ Quality badge** — Every completed download shows you the actual resolution you received.
- **📊 Live progress** — See real-time speeds, percentages, and time remaining right in your browser corner.
- **⏸️ Full control** — Pause, Resume, or Cancel your downloads at any time.
- **🔄 Auto-healing** — Behind the scenes, we automatically handle YouTube's tricky updates so your video always downloads.
- **🔒 100% private** — Videos save straight to your computer. No servers. No tracking. No data collection.
- **🆓 Free & open source** — Yours to use forever!

---

## 🖥️ Supported Browsers

Works perfectly on Windows, Mac, and Linux!

| Chrome | Brave | Edge | Chromium |
|---|---|---|---|
| ✅ | ✅ | ✅ | ✅ |

---

## 🚀 How to Install — Quick Setup

### 🪟 Windows Setup

**Step 1: Download the Extension Folder**
- Scroll to the top of this page and click the green **<> Code** button.
- Click **Download ZIP**.
- Extract this ZIP file into a permanent folder (like your Documents or Desktop).

**Step 2: Add it to your Browser**
- Open Chrome, Brave, or Edge and go to your extensions settings (type `chrome://extensions` in the address bar).
- Turn on **Developer mode** in the top right corner.
  ![Visual Guide to Developer Mode](https://developer.chrome.com/docs/extensions/mv3/getstarted/development-basics/image/chrome-extensions-developer-mode-toggle.png)
- Click the **Load unpacked** button.
- Find your extracted folder, go inside it, and select the folder named `extension`.
- FlashYT is now in your browser! Note the long string of letters next to "ID:" under FlashYT — **copy that ID**, you will need it in the next step.

**Step 3: Run the Setup Installer**
- Head over to the [FlashYT Releases](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest) page.
- Download the **`FlashYT_Installer_v2.1.9.exe`** file and run it. *(This tiny installer automatically handles all the complicated background tech so you don't have to!)*
- If Windows says "Windows protected your PC", just click **"More info" → "Run anyway"**.
- Proceed through the installation. At the end, it will ask for your Extension ID. **Paste the ID you copied from Step 2**.
- Finish the installation.
- Finally, go back to your browser extensions page and click the little **🔄 reload icon** on the FlashYT card. 

You're done! 🎉

---

### 🍎 macOS & 🐧 Linux Setup

**Step 1: Add it to your Browser**
- Follow Windows Steps 1 and 2 above. Download the ZIP from the green Code button, extract it, and load the `extension` folder into your browser.
- *(Note: On Mac and Linux, you do not need to copy the Extension ID. It will automatically detect it!)*

**Step 2: Run the Setup Command**
Don't let the code scare you! Just open the app called **Terminal** on your Mac or Linux computer, paste this exact line, and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
```

That's it! It automatically sets up all the background magic. Go to your extensions page and click **🔄 reload** on FlashYT.

---

## 🎬 How to Use

1. Open any YouTube video!
2. Click the friendly red **⚡ Download** button right beneath the video.
3. Pick your quality — **1080p**, **4K**, or **audio only**.
4. Your download starts instantly. Click the FlashYT icon in your browser to watch it download!

> **Friendly Tip:** Sign into YouTube first! Being logged into your account lets FlashYT grab the highest 4K and HD qualities without YouTube blocking them.

---

## 🔄 How to Update

When a new version comes out, you'll see a red "Update Available" banner in FlashYT.

To update, just follow this one foolproof rule:
1. Download the new `Source code (zip)` from our releases page.
2. Extract it, and **copy/paste the new files directly over your existing FlashYT folder**. 
3. When your computer asks, choose **"Replace All"**.
4. IMPORTANT: **Never delete your old folder first!** Always overwrite the files.

Then, just click the **🔄 Reload icon** in your extensions page and completely restart your browser. The red banner will vanish!

---

## 🔧 Simple Troubleshooting

### "Host not connected" or "Disconnected"
This just means the background helper isn't running. 
- **Windows:** Double-click your `.exe` installer again.
- **Mac/Linux:** Open Terminal and run the install command from above.
Then, reload the extension!

### Download stuck at 0%
Just make sure you're updated to the latest version of FlashYT. YouTube changes things often, and our updates fix them instantly!

### Missing Download Button
Just refresh the YouTube page, or make sure the extension is turned on in your browser settings.

---
<<<<<<< HEAD

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
=======
*Created by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
>>>>>>> de8432b (docs: complete rewrite of README for non-technical users)
