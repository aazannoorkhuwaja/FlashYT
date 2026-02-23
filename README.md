# One-Click YouTube Downloader (yt-dlp + Flask)

**Built by Aazan Noor Khuwaja**

A seamless YouTube downloading experience integrated directly into your browser via Tampermonkey. Click Download on any YouTube video, pick your quality (144p to 4K), and it drops straight into your Downloads folder — all within 1 second.

## 🌟 Key Features
1. **Instant Quality Selection**: Click Download → pick 1080p, 720p, 4K, or Audio-Only → download starts in under 1 second.
2. **Multi-Tasking**: Download 5+ videos simultaneously with independent progress tracking via a floating dashboard.
3. **Smart Background Prefetch**: Qualities are fetched silently the moment you open a video page — the modal appears instantly.
4. **Auto Browser Detection**: Automatically finds your installed browser (Brave, Chrome, Firefox, Edge, etc.) for cookie import.
5. **Auto-Start on Boot**: Run setup once and the server starts automatically on every boot — zero maintenance forever.
6. **First-Time Folder Picker**: On first download, a native OS dialog lets you choose your download folder.

---

## 🌐 Browser Compatibility

| Browser | Supported | Notes |
|---------|-----------|-------|
| Google Chrome | ✅ | Full support |
| Brave | ✅ | Full support |
| Mozilla Firefox | ✅ | Full support via Tampermonkey/Greasemonkey |
| Microsoft Edge | ✅ | Full support |
| Opera / Opera GX | ✅ | Full support |
| Safari | ⚠️ | Requires Userscripts app from App Store |

---

## 🚀 Setup — Linux (One Command!)

```bash
git clone https://github.com/aazannoorkhuwaja/one_click_ytmp4_download.git
cd one_click_ytmp4_download
chmod +x setup.sh && ./setup.sh
```

## 🚀 Setup — Windows (One Command!)

```
git clone https://github.com/aazannoorkhuwaja/one_click_ytmp4_download.git
cd one_click_ytmp4_download
setup.bat
```

> **Don't have Git?** Just download the ZIP from the green **Code** button above, extract it, and double-click `setup.bat`.

### What the Setup Does (Both Platforms)
- ✅ Installs Python, FFmpeg, and all dependencies automatically
- ✅ Creates a Python virtual environment with all packages
- ✅ Sets up auto-start on every boot (systemd on Linux, Startup folder on Windows)
- ✅ Auto-updates yt-dlp on every restart to keep up with YouTube changes
- ✅ Verifies everything is working

### After Setup — Install the Browser Extension
1. Install [Tampermonkey](https://www.tampermonkey.net/) in your browser
2. Click the Tampermonkey icon → **Create a new script**
3. Delete everything → paste the contents of `userscript.js` → **Ctrl+S** to save
4. Go to YouTube, play any video, and click the red **Download** button! 🎉

---

## 🛠️ Useful Commands

### Linux
| Action | Command |
|--------|---------|
| Check if server is running | `systemctl --user status yt-downloader` |
| Restart the server | `systemctl --user restart yt-downloader` |
| Stop the server | `systemctl --user stop yt-downloader` |
| View live logs | `journalctl --user -u yt-downloader -f` |

### Windows
The server runs silently in the background (no terminal window). To stop it, open Task Manager and end `pythonw.exe`.

---

*Vibe coded* 🎵
