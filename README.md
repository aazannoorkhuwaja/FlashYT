# FlashYT ⚡ v2.2.2

> **The easiest, most reliable free YouTube downloader — right in your browser.**
> No cloud. No accounts. No limits. One click and it's yours — in exactly the quality you want.

![FlashYT Icon](https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/extension/icons/icon128.png)

[![Version](https://img.shields.io/github/v/release/aazannoorkhuwaja/FlashYT?label=version&color=brightgreen)](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## ✨ Why FlashYT?

FlashYT is built to **just work** — for everyone, on every computer, in every browser.

- **⚡ One-click download** — A friendly Download button appears directly under YouTube videos! No copying and pasting links.
- **🎯 Exact quality over promises** — Get exactly what you pick, from **1080p to 4K/8K Ultra HD** and high-bitrate Audio.
- **✅ Quality badge** — Every completed download shows you the actual resolution you received.
- **📊 Live progress** — See real-time speeds, percentages, and time remaining right in your browser corner.
- **⏸️ Full control** — Pause, Resume, or Cancel your downloads at any time.
- **🔄 Auto-healing** — Behind the scenes, we automatically handle YouTube's tricky updates so your video always downloads.
- **🖥️ System Tray** — A lightweight tray icon (on Windows) gives you quick access to logs and status.
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

### 🪟 Windows Setup — One-Click Install

1. **Download the installer** from the [Releases page](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest) → `FlashYT-setup.exe`
2. **Run it** (double-click). If Windows shows a "Windows protected your PC" message, click **More info → Run anyway**. *(This is normal for open-source apps not yet recognized by Microsoft.)*
3. Click **Next → Next → Install**.
4. When installation completes: **close Chrome completely** and reopen it.
5. FlashYT appears in your extensions automatically — no manual steps needed!
6. Visit any YouTube video and click **⚡ Download**. That's it!

> **Note:** When you first reopen Chrome, it may show a bar at the top: *"Extensions in developer mode."* Click the **✕** to dismiss it. It will never appear again.

---

### 🍎 macOS & 🐧 Linux Setup

1. **Open your Terminal** app.
2. **Paste these exact lines** and press Enter:

```bash
curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh
chmod +x install.sh
bash install.sh
```

> **Why three lines?** The installer needs to ask technical questions about your environment. The single-line `curl | bash` method prevents it from doing that. These three lines take the same amount of time and work correctly.

---

## ⚙️ Configuration (.env)

FlashYT supports advanced configuration via a `.env` file in the root directory. You can use `.env.example` as a template:

- `FLASHYT_INNERTUBE_KEY`: Your YouTube API key (optimizes quality discovery).
- `FLASHYT_VERIFY_SSL`: Toggle SSL verification (for specific network proxies).
- `FLASHYT_MAX_CONCURRENT`: Limit the number of simultaneous download parts.

---

## 🎬 How to Use

1. **Open any YouTube video!**
2. Click the friendly red **⚡ Download** button right beneath the video.
3. Pick your quality — **1080p**, **4K**, or **audio only**.
4. Your download starts instantly. Click the **FlashYT icon** (top right of browser) to watch it download!

> [!TIP]
> **Windows Users:** Check your System Tray (near the clock) for the FlashYT icon! You can right-click it to check connectivity or view logs.

---

## 🔄 How to Update

FlashYT now features **Auto-Update Notifications**! 🚀

1. When a new version is available, a **red "Update Available" banner** will appear inside the FlashYT extension popup.
2. Simply click the **Update** button (or follow the link provided).
3. Download the new installer (Windows) or re-run the setup command (Mac/Linux).
4. Click the **🔄 Reload icon** in your browser's extension settings.

---

## 🔧 Simple Troubleshooting

### "Windows protected your PC" during installation
Click **More info** then **Run anyway**. This message appears for all open-source software that hasn't yet been widely downloaded. FlashYT is safe and open source — you can read every line of code on GitHub.

### Chrome shows "Extensions in developer mode" banner
Click the **✕** on the right side of that bar to dismiss it. It will never appear again. This is a standard Chrome notice for extensions installed outside the Chrome Web Store.

### "Host not connected" or "Disconnected"
- **Windows:** Run the installer again or start `host.exe` from your installation folder.
- **Mac/Linux:** Re-run the setup commands from above.

---

## 📋 Reading the Log (for debugging)

| OS | Log file path |
|---|---|
| Linux / macOS | `~/.config/YouTubeNativeExt/host.log` |
| Windows | `%APPDATA%\YouTubeNativeExt\host.log` |

---

## 🗑️ Uninstall

**Linux / macOS:**
```bash
curl -L -o uninstall.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/uninstall.sh
chmod +x uninstall.sh
./uninstall.sh
```

**Windows:** Use Windows → Add/Remove Programs → uninstall FlashYT.

---

## 📄 License

MIT — free to use, share, and modify. See [LICENSE](LICENSE) for details.

---

*Vibe Coded by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
