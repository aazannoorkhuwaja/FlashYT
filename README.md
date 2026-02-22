# One-Click YouTube Downloader (yt-dlp + Flask)

**Built by Aazan Noor Khuwaja**

A seamless YouTube downloading experience integrated directly into your browser via Tampermonkey. It automatically bypasses YouTube bot protections and drops files directly into your `Downloads` folder using the fastest available quality (up to 1080p) combined with high-quality audio.

## 🌟 Key Features
1. **Multi-Tasking**: You can click download on 5 different YouTube videos at the same time. The server handles them all in parallel with independent UI progress tracking!
2. **One-Click Native App**: No Python required! You can download the pre-compiled `.exe` (Windows) or Linux binary, double click it, and the server runs silently in the background.
3. **Smart URL Detection**: Automatically strips playlist parameters from URLs — even if you're watching a video in a playlist or mix, it downloads only the specific video you're on.
4. **Auto Browser Detection**: Automatically finds your installed browser (Brave, Chrome, Firefox, Edge, etc.) for cookie import — no manual configuration needed.
5. **Customizable Settings**: Click the ⚙️ gear icon on YouTube to change your download folder or browser settings at any time.
6. **Auto-Start on Boot**: The setup script configures the server to start automatically when your computer turns on — run setup once and forget about it forever.

---

## 🌐 Browser Compatibility

This extension works on **any browser that supports Tampermonkey**:

| Browser | Supported | Notes |
|---------|-----------|-------|
| Google Chrome | ✅ | Full support |
| Brave | ✅ | Full support |
| Mozilla Firefox | ✅ | Full support via Tampermonkey/Greasemonkey |
| Microsoft Edge | ✅ | Full support |
| Opera / Opera GX | ✅ | Full support |
| Safari | ⚠️ | Requires Userscripts app from App Store |

The server **auto-detects** which browser you have installed — no manual configuration needed!

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

## 💻 Developer Setup (Linux — One Command!)

```bash
# Clone and run setup — that's it!
git clone https://github.com/aazannoorkhuwaja/one_click_ytmp4_download.git
cd one_click_ytmp4_download
./setup.sh
```

The setup script will:
- ✅ Install `python3`, `ffmpeg`, and all dependencies automatically
- ✅ Create a virtual environment with all Python packages
- ✅ Set up a background service that **auto-starts on every boot**
- ✅ Verify everything is working

After setup, just install the Tampermonkey userscript (the setup will tell you how).

---

## ⚙️ Changing Settings

Click the **⚙️ gear icon** next to the Download button on any YouTube video to:

- 📁 **Change download folder** — save videos anywhere you want
- 🌐 **Change browser** — switch between Auto-Detect, Chrome, Brave, Firefox, Edge, etc.

Settings are saved permanently and survive reboots.

---

## 🛠️ Useful Commands

| Action | Command |
|--------|---------|
| Check if server is running | `systemctl --user status yt-downloader` |
| Restart the server | `systemctl --user restart yt-downloader` |
| Stop the server | `systemctl --user stop yt-downloader` |
| View live logs | `journalctl --user -u yt-downloader -f` |

---

*Vibe coded* 🎵
