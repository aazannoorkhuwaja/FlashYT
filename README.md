# One-Click YouTube Downloader 🚀
<p align="center">
  <em>The ultimate, zero-maintenance background downloader that integrates natively into YouTube. Designed for speed, built for complete resilience.</em>
</p>

---

## 🌟 Why This Exists (The "SaaS" Experience)

Most downloaders are clunky websites filled with ads, or fragile scripts that break the moment YouTube updates its bot detection. **One-Click YouTube Downloader** is designed to feel like a premium, native extension of YouTube itself.

*   ⚡ **Zero Wait Times:** Quality options (144p to 4K) are pre-fetched silently in the background the moment you open a video page. Clicking "Download" is instant.
*   🛡️ **Invincible Anti-Bot Evasion:** Completely immune to YouTube's latest DRM, Age-Restriction, and Proof of Origin (PO) Token blocks. We utilize dynamic browser impersonation and auto-negotiate clients via the nightly `yt-dlp` suite.
*   💻 **Zero-Dependency Native App:** No Python or FFmpeg PATH nightmares. Everything is bundled into a single standalone executable.
*   🎨 **Beautiful UI Overlays:** Features a sleek dark-mode quality selection modal and a draggable, real-time download dashboard injected right into the YouTube player.
*   ⚙️ **System Tray & Web UI:** Manage your download folders and browser privacy settings seamlessly via a native Web UI accessible straight from your OS system tray.

---

## 🚀 1-Minute Setup (Windows)

1. **Download** the latest `youtube-downloader-windows.exe` from the [**Releases Page**](../../releases/latest).
2. **Run it!** That's it. It will silently bundle its own FFmpeg environment, boot the local server, and embed a sleek icon in your System Tray. It configures itself to auto-start on every boot.

### Install the Native UI (All Platforms)
1. Install the [Tampermonkey](https://www.tampermonkey.net/) extension for your browser.
2. Click the Tampermonkey icon → **Create a new script**.
3. Clear the editor, paste the contents of [`userscript.js`](userscript.js), and press **Ctrl+S** (Save).
4. Go to any YouTube video and click the red **Download** button! 🎉

---

## 🐧 1-Command Setup (Linux / macOS)

For Linux and macOS power users, we provide a self-healing, bulletproof setup script. It automatically maps your package manager (`apt`, `dnf`, `pacman`, `zypper`), manages dependencies, and registers a background systemd service.

```bash
git clone https://github.com/aazannoorkhuwaja/one_click_ytmp4_download.git
cd one_click_ytmp4_download
chmod +x setup.sh && ./setup.sh
```

**Note:** If you ever accidentally break your local files, the background service will automatically run a `git reset --hard` on boot to securely heal itself from the main branch.

---

## 🌐 Browser Compatibility (For Age-Restricted Cookies)

The downloader automatically scans your OS for active browsers to intelligently import session cookies, allowing you to seamlessly download Age-Restricted or Members-Only videos without lock errors:

| Browser | Supported |
|---------|-----------|
| Google Chrome | ✅ |
| Brave | ✅ |
| Mozilla Firefox | ✅ |
| Microsoft Edge | ✅ |
| Opera / Opera GX | ✅ |

*You can swap which browser is prioritized at any time by right-clicking the Downloader System Tray icon and selecting **Settings**.*

---

## 🛠️ Architecture & Security

*   **100% Local Processing:** The backend Flask server binds exclusively to `127.0.0.1:5000`. No external data collection, no open ports, completely private.
*   **Cookie Safe-Copying:** Avoids aggressive "SQLite Database is Locked" errors by dynamically generating shadow-copies of your browser data into temporary files during extraction.

> Built and constantly iterated by **Aazan Noor Khuwaja**.
