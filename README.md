# YouTube Native Downloader

A strictly local, blazing-fast native Chrome extension to download any YouTube video in one click. No web services, no SaaS accounts, and absolutely no privacy-invading metrics.

![YouTube Native Downloader](extension/icons/icon128.png)

## Download & Install

### Windows
1. Download the installer below:
   [**Download for Windows (.exe)**](https://github.com/aazannoorkhuwaja/youtube-native-ext/releases/latest)
2. Run it (double-click the downloaded `.exe` file).
3. Install the browser extension [from the Chrome Web Store (not published yet)].
   *(If installing from source, enable Developer Mode in `chrome://extensions` and load the unpacked `extension` directory).*

Done!

### Mac / Linux
Open your terminal and paste this command:
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/youtube-native-ext/main/install.sh | bash
```
Then install the browser extension [from the Chrome Web Store (not published yet)].

## How It Works
Unlike traditional web downloaders or buggy Tampermonkey scripts, this product creates a secure Native Messaging pipe between your Google Chrome browser and a local `yt-dlp` micro-host running directly on your computer. Your downloads never touch our servers. It uses your IP address, completely bypassing YouTube's bot-detection algorithms that break cloud-hosted websites.

## Why It Works When Others Don't
Because there is no external server, there are no CORS (Cross-Origin Resource Sharing) security violations. You click "Download", your browser silently pings the local host on your machine, and the host streams the bytes directly into your native Downloads folder. It is perfectly private by design. 

## Troubleshooting

**Q: The Download button doesn't appear**
A: Make sure the desktop app natively installed successfully. If you change browsers (e.g., from Chrome to Brave), you may need to re-run the installer script so it can bind to the new Browser's registry.

**Q: "Desktop app not running" or "Host not connected" error**
A: Reinstall the desktop app. Ensure that you haven't moved the installation directory after installing. If the problem persists, open an issue targeting the `host.log` file.

**Q: Download stuck or failed**
A: Check the log file. You can automatically open it by clicking the extension icon in your browser toolbar, navigating to the "About" tab, and clicking **View Debug Log**.

## Contributing
Contributions are always welcome. Please make sure to test the Native Messaging protocol using standard Python `stdin/stdout` pipes before submitting PRs altering `host.py`.

## License
MIT
