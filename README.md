# 🚀 YouTube Native Downloader

A strictly local, blazing-fast native Chrome extension to download any YouTube video in one click. No web services, no SaaS accounts, and absolutely no privacy-invading metrics.

![YouTube Native Downloader](extension/icons/icon128.png)

### Why This Exists (And Why It Works When Others Fail)
Most YouTube downloader extensions on the Chrome Web Store break every few weeks, slow down your browser, or are packed with hidden ads. This happens because YouTube constantly changes its underlying code to block direct browser downloads.

**The Solution:** This extension is a true **Native Desktop App** cleverly disguised as a browser button. It brings the power of the legendary `yt-dlp` command-line engine directly to your Chrome browser. It downloads videos instantly in 1-Click straight to your hard drive, completely ad-free and tracking-free. Best of all, it has a built-in **"Update Core Engine"** button, meaning if YouTube ever changes their systems, you can self-patch the app in exactly 3 seconds!

> [!IMPORTANT]
> Because this is a powerful Native Desktop application, Google does not allow it on the standard Chrome Web Store. You must install it manually in two very quick steps: loading the un-packaged browser extension, and installing the invisible desktop engine.

---

## 🛠️ Step-by-Step Installation

### Step 1: Add the Button to Chrome / Brave
1. Download the latest source code `.zip` from the [GitHub Releases Page](https://github.com/aazannoorkhuwaja/youtube-native-ext/releases).
2. Extract the downloaded `.zip` file into a permanent folder on your computer (e.g., inside your `Documents` folder). **Do not delete this folder later, or the extension will break!**
3. Open your browser and type `chrome://extensions` in the URL address bar (or `brave://extensions` if using Brave).
4. Turn **ON** the **"Developer mode"** toggle switch in the top right corner.
5. Click the **"Load unpacked"** button in the top left.
6. Select the `extension` folder located inside the files you just extracted.
*(The red YouTube Downloader icon should now appear in your browser extensions list!)*

### Step 2: Install the Desktop Engine
The browser button now exists, but it needs its background engine to actually download the massive video files to your computer.
* **For Windows:** Double-click the `youtube-native-downloader-setup.exe` (if you downloaded the Windows release) OR run the `scripts/build_windows.bat` file.
* **For Mac / Linux:** Open your terminal, navigate inside the extracted folder, and run: `bash install.sh`

🎉 **You are completely done!** Go to any YouTube video and click the newly injected red **⬇ Download** button right beneath the video player.

---

## 🛑 Common Issues & Troubleshooting

#### ❌ Error: "Desktop app not running" or UI status says "Disconnected"
**Solution:** The browser extension cannot find the background desktop engine.
1. Make sure you actually completed **Step 2** and ran the installer script.
2. If you moved or renamed the extraction folder *after* loading the extension into Chrome, the connection is fundamentally broken. Go to `chrome://extensions`, click "Remove" on the extension, and repeat Step 1 from the new folder location. Then, run the installer script again.

#### ❌ Downloads are suddenly freezing at 0% or failing completely!
**Solution:** YouTube likely updated their cipher codes to block downloads. *This is exactly why we built the auto-updater!*
1. Click the red Downloader Extension icon in the top right corner of Chrome to open the popup UI.
2. Go to the **About** tab.
3. Click the **"Update Core Engine"** button. 
4. A background task will fetch the absolute newest `yt-dlp` patches. Wait about 10 seconds, refresh your YouTube page, and your downloads will instantly work again!

#### ❌ Error: "Requested format is not available"
**Solution:** The specific YouTube video you are watching does not have the exact video resolution you selected (for example, you tried to download 1080p, but the creator only uploaded it in 720p maximum). Click the button again and select a different quality option.

#### ❌ The red Download button randomly disappears
**Solution:** Simply **Refresh the page (`F5` or `Ctrl+R`)**. Because YouTube is a "Single Page Application", it sometimes loads new videos without actually refreshing your browser tab, which can occasionally hide the injected button.

## Contributing
Contributions are always welcome. Please make sure to test the Native Messaging protocol using standard Python `stdin/stdout` pipes via `pytest tests/test_protocol.py` before submitting PRs altering `host.py`.

## License
MIT
