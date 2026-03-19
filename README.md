<h1 align="center">⚡ FlashYT</h1>

<p align="center">
  <strong>One-click YouTube video downloader — runs directly inside your browser.</strong><br>
  No accounts. No cloud. No subscriptions. 100% private.
</p>

<p align="center">
  <a href="https://github.com/aazannoorkhuwaja/FlashYT/releases/latest">
    <img src="https://img.shields.io/github/v/release/aazannoorkhuwaja/FlashYT?color=brightgreen&label=Latest" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License">
  </a>
  <a href="https://github.com/aazannoorkhuwaja/FlashYT/stargazers">
    <img src="https://img.shields.io/github/stars/aazannoorkhuwaja/FlashYT?style=social" alt="Stars">
  </a>
</p>

---

## Overview

FlashYT adds a **Download** button directly under every YouTube video. Select a quality, click download — that's it. Downloads happen locally on your machine with live progress tracking.

![FlashYT Demo](docs/images/flashyt_demo.gif)

**Key capabilities:**
- Download in any quality, up to **4K / 8K**
- Live progress bar with speed, percentage, and ETA
- Pause, resume, and cancel downloads
- Supports Chrome, Brave, Edge, and all Chromium-based browsers
- Works on Windows, macOS, and Linux

---

## Requirements

- A **Chromium-based browser** (Chrome, Brave, Edge, etc.)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and [`ffmpeg`](https://ffmpeg.org/) — installed automatically by the setup scripts

---

## Installation

> **After installing or updating**, you must reload the extension at `chrome://extensions` by clicking the **🔄 Reload** icon on the FlashYT card.

### Windows

**Option A — PowerShell (recommended)**
```powershell
irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.ps1 | iex
```

**Option B — Manual**
1. Download [`FlashYT-setup.exe`](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest) from the Releases page.
2. Run the installer. If Windows shows a SmartScreen warning, click **More info → Run anyway**.
3. Load the extension (see [Loading the Extension](#loading-the-extension)).

---

### macOS / Linux

**Option A — Terminal one-liner (recommended)**
```bash
curl -L https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
```

**Option B — Manual**
```bash
curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh
chmod +x install.sh
bash install.sh
```

The script auto-detects your package manager (`apt`, `dnf`, `pacman`, or `brew`) and installs `ffmpeg` and all Python dependencies.

---

## Loading the Extension

Because FlashYT is not on the Chrome Web Store, the extension must be loaded manually. This is a one-time step.

1. Open your browser's extensions page:
   | Browser | URL |
   |---------|-----|
   | Chrome | `chrome://extensions` |
   | Brave | `brave://extensions` |
   | Edge | `edge://extensions` |

2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the `extension` folder:
   - **Windows:** `%localappdata%\Programs\FlashYT\extension`
   - **macOS / Linux:** The `extension` folder inside the downloaded ZIP or repo.

5. Open any YouTube video — the ⚡ Download button will appear below the player.

---

## Updating

Use the same commands as installation. The scripts are idempotent — they safely overwrite the previous version.

| Platform | Command |
|----------|---------|
| **Windows (PowerShell)** | `irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.ps1 \| iex` |
| **macOS / Linux** | `curl -L https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh \| bash` |

After updating the host, **reload the extension** at `chrome://extensions`.

---

## Manual Dependency Setup (Advanced)

If the automated scripts fail, install dependencies manually:

```bash
# Ubuntu / Debian
sudo apt install ffmpeg python3-pip
pip3 install yt-dlp pystray Pillow secretstorage

# Arch Linux
sudo pacman -S ffmpeg python-pip yt-dlp

# Fedora
sudo dnf install ffmpeg python3-pip
pip3 install yt-dlp pystray Pillow
```

Then run the setup script from the repository root:
```bash
bash install.sh
```

---

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| **"Host not connected"** | Re-run the installer, then reload the extension at `chrome://extensions` |
| **Extension not visible** | Ensure Developer mode is enabled and the correct `extension` folder was selected |
| **Download stuck at 0%** | Re-run the installer to update `yt-dlp` to the latest version |
| **Download button missing** | Hard-refresh YouTube: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS) |
| **Antivirus blocking** | Add FlashYT to your antivirus exceptions and re-run the installer |

### Log Files

For detailed diagnostics, inspect the host log:

| Platform | Log location |
|----------|-------------|
| Windows | `%APPDATA%\YouTubeNativeExt\host.log` |
| macOS / Linux | `~/.config/YouTubeNativeExt/host.log` |

[Open a GitHub issue](https://github.com/aazannoorkhuwaja/FlashYT/issues) and paste the log contents if you need further assistance.

---

## Configuration

Create a `.env` file in the `host` directory (copy from `.env.example`) to customize behaviour:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASHYT_MAX_CONCURRENT` | `3` | Maximum simultaneous downloads |
| `FLASHYT_INNERTUBE_KEY` | *(auto)* | Custom InnerTube API key for quality detection |
| `FLASHYT_SKIP_SSL_VERIFY` | `0` | Set to `1` (or `FLASHYT_VERIFY_SSL=0`) to disable SSL verification |
| `FLASHYT_PREFETCH_TIMEOUT` | `10` | Timeout in seconds for quality prefetching |

---

## Android App

FlashYT also has an Android app! It allows you to download videos directly from the YouTube share sheet without a server. See [android/README.md](android/README.md) for build and installation instructions.

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<p align="center">
  Built by <a href="https://www.linkedin.com/in/aazan-noor-khuwaja-cs/">Aazan Noor Khuwaja</a>
</p>
