# FlashYT ⚡

> **The easiest, most reliable free YouTube downloader — right in your browser.**
> No cloud. No accounts. No limits. One click and it's yours — in exactly the quality you want.

![FlashYT Icon](https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/extension/icons/icon128.png)

[![Version](https://img.shields.io/github/v/release/aazannoorkhuwaja/FlashYT?label=version&color=brightgreen)](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

## ✨ Why FlashYT?

FlashYT is built to **just work** — for everyone, on every computer, in every browser.

- **⚡ One-click download** — A friendly Download button appears directly under YouTube videos!
- **🎯 Exact quality** — Get exactly what you pick, from **1080p to 4K/8K Ultra HD**.
- **📊 Live progress** — See speeds, percentages, and time remaining in real-time.
- **🖥️ System Tray** — Windows tray icon for quick status and logs.
- **🔒 100% private** — Videos save straight to your computer. No servers.
- **🆓 Free & open source** — Yours to use forever!

---

## 🚀 Installation

### 🪟 Windows — One-Click Setup
1. Download `FlashYT-setup.exe` from [Releases](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).
2. Run the installer. If prompted with "Windows protected your PC", click **More info → Run anyway**.
3. Reopen Chrome/Brave/Edge. FlashYT is ready!

### 🍎 macOS & 🐧 Linux — 3-Step Setup
1. Open Terminal and Paste:
```bash
curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh
chmod +x install.sh
bash install.sh
```

---

## 🎬 Screenshots

| Popup Progress | Download Button |
|---|---|
| ![Popup](https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/docs/images/popup_preview.png) | ![Button](https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/docs/images/button_preview.png) |

---

## ⚙️ Configuration (.env)
FlashYT uses a `.env` file for optional settings. See `.env.example` to configure:
- `FLASHYT_INNERTUBE_KEY`: For faster quality prefetching.
- `FLASHYT_MAX_CONCURRENT`: Limit simultaneous download streams.

---

## 📋 Debugging
| OS | Log Path |
|---|---|
| Linux / macOS | `~/.config/YouTubeNativeExt/host.log` |
| Windows | `%APPDATA%\YouTubeNativeExt\host.log` |

---

## 🗑️ Uninstall
**Mac/Linux:**
```bash
curl -L -o uninstall.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/uninstall.sh
chmod +x uninstall.sh
./uninstall.sh
```
**Windows:** Use "Add or Remove Programs" in Windows Settings.

---

## 📄 License
MIT — free to use and modify. See [LICENSE](LICENSE).

---

*Vibe Coded by [Aazan Noor Khuwaja](https://www.linkedin.com/in/aazan-noor-khuwaja-cs/)*
