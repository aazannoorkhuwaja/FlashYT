# FlashYT

Fast, local-first YouTube downloader built as a browser extension + native host.
Your video data stays on your machine.

![FlashYT](extension/icons/icon128.png)

## Why FlashYT

- Real-time progress in both YouTube page button and popup queue
- Cross-platform native host support for Windows, Linux, and macOS
- No cloud relay for downloads

## Supported Browsers

- Google Chrome
- Brave
- Microsoft Edge
- Chromium

## Important Before You Start

1. Install the browser extension first, then the native host.
2. Keep the install path stable after setup.
3. If you switch browser or browser profile, run setup again.
4. For repeated format/prefetch failures, sign in to YouTube in the same browser profile.

## 1) Install the Browser Extension

### Option A: Chrome Web Store (recommended when published)
1. Install FlashYT from the store listing.
2. Continue to OS setup below.

### Option B: Load from source (available now)
1. Open extensions page:
`chrome://extensions` or `brave://extensions` or `edge://extensions`
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select the `extension/` folder from this repo.
5. Keep extension enabled, then run setup script/installer.

## 2) Native Host Setup by OS

### Windows
1. Download the latest installer:
[Download Windows installer (.exe)](https://github.com/aazannoorkhuwaja/youtube-native-ext/releases/latest)
2. Run the installer.
3. Installer auto-detects extension ID(s) and registers native host.
4. Restart browser.

### Linux
1. Run:
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/youtube-native-ext/main/install.sh | bash
```
2. Setup auto-detects extension ID(s) and registers native host.
3. Restart browser.

### macOS
1. Run:
```bash
curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/youtube-native-ext/main/install.sh | bash
```
2. Setup auto-detects extension ID(s) and registers native host.
3. Restart browser.

## 3) Verify in 60 Seconds

1. Open any YouTube watch page.
2. Confirm FlashYT button appears near video actions.
3. Start one download.
4. Confirm progress updates live in:
- YouTube button
- Popup `Queue` row
5. Test `pause`, `resume`, and `cancel`.

## Common Issues and Solutions

### 1) Button not visible on YouTube
1. Refresh the tab.
2. Confirm extension is enabled.
3. Reload extension from browser extensions page.
4. Re-run native host setup.

### 2) "Host not connected" error
1. Re-run installer/setup for your OS.
2. Confirm FlashYT extension is installed and enabled in your active browser profile.
3. Restart browser after setup.

### 3) "Failed to fetch qualities" or prefetch timeout
1. Sign in to YouTube and retry.
2. Refresh the video page and reopen quality selector.
3. Reduce heavy parallel activity and retry.
4. If persistent, collect `host.log` and open an issue.

### 4) Pause/resume feels out of sync under heavy concurrency
1. Keep `Max Concurrent` at `2-4` for best stability.
2. Pause one item, wait a moment, then resume.
3. Reopen popup if queue UI looks stale.

### 5) Linux popup asks to open external app for email
This is fixed in current builds: email uses copy-to-clipboard in About section.
If you still see prompt behavior, reload extension to latest code.

### 6) Windows SmartScreen/Defender warns on installer
1. Always download from official GitHub Releases.
2. Use the latest signed release build (code-signing step in CI).
3. If your org policy blocks unknown publishers, ask IT to trust your signing certificate thumbprint.
4. Verify SHA256 checksum of release assets before install.

## Log File Locations

- Linux/macOS: `~/.config/YouTubeNativeExt/host.log`
- Windows: `%APPDATA%\YouTubeNativeExt\host.log`

## Feedback

Report bugs and suggestions:
1. GitHub Issues: https://github.com/aazannoorkhuwaja/youtube-native-ext/issues
2. Include:
- OS + browser + browser version
- FlashYT extension version
- Exact reproduction steps
- Exact error text shown
- Relevant lines from `host.log`

## User Guidance (Recommended)

1. Set `Max Concurrent` to `2-4` for consistent behavior.
2. Prefer local SSD save location for better merge speed.
3. Stay signed in on YouTube for fewer format-fetch failures.
4. Reload extension after pulling repo updates.

## Contributing

PRs are welcome. If your change touches host protocol or queue states, run host tests and verify native messaging flows before submitting.

## License

MIT
