<h1 align="center">⚡ FlashYT</h1>

<p align="center">
  <strong>A browser extension with a local companion app for downloading YouTube videos.</strong><br>
  Choose formats and monitor download progress from your browser.
</p>

<p align="center">
  <a href="https://github.com/aazannoorkhuwaja/FlashYT/releases/latest">
    <img src="https://img.shields.io/github/v/release/aazannoorkhuwaja/FlashYT?color=brightgreen&label=Latest" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-lightgrey" alt="Platform">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License">
  </a>
</p>

---

## ⚡ Overview

FlashYT adds a **Download** action to supported YouTube pages. The browser extension sends requests to a local Python host, which manages downloads through `yt-dlp`.

![FlashYT Demo](docs/images/flashyt_demo.gif)

[Download button](docs/images/yt_download_button.png) · [Quality selection](docs/images/quality_selector.png) · [Active download queue](docs/images/active_queue.png)

✨ **Key features**
- **Quality selection:** Choose from the formats available for a video.
- **Local processing:** A companion host handles downloads instead of a remote FlashYT service.
- **Progress tracking:** View the status of active downloads.
- **Browser integration:** Extension support for Chrome, Edge, and Brave; platform setup instructions are below.

---

## 🚀 Installation

FlashYT has two parts: the local background app (host) and the browser extension.

### Step 1: Install the App (Host)

**🖥️ Windows Users:**
1. Download **`FlashYT-setup.exe`** from the [Latest Release page](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).
2. Double-click the file to run the installer. *(If Windows shows a blue "Windows protected your PC" popup, just click **More info** -> **Run anyway**).*

**🍏 Mac & 🐧 Linux Users:**
1. Open the **Terminal** app.
2. Paste this exact command and hit Enter:
   ```bash
   curl -sSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash
   ```

---

### Step 2: Add the Button to your Browser (Extension)

Since FlashYT isn't in the Chrome Web Store, you just need to load it manually once.

1. Open your browser and go to the extensions page:
   - **Chrome**: Type `chrome://extensions` in the address bar.
   - **Edge**: Type `edge://extensions` in the address bar.
   - **Brave**: Type `brave://extensions` in the address bar.
2. Turn ON **Developer mode** (a toggle switch usually in the top-right corner).
3. Click the **Load unpacked** button.
4. Select the `extension` folder:
   - **Windows:** Copy and paste `%LOCALAPPDATA%\Programs\FlashYT\extension` into the folder selection bar and hit Select Folder.
   - **Mac/Linux:** Select the `extension` folder that the installer opened up for you.

---

### Step 3: You're Done! 🎉
Go open any YouTube video and refresh the page. You will see the new **⚡ Download** button right under the video player!

---

## 📱 FlashYT for Android

FlashYT also has an Android app that lets you download videos directly from the YouTube app's share menu.
1. Download the `FlashYT-...-debug.apk` file from the [Releases page](https://github.com/aazannoorkhuwaja/FlashYT/releases/latest).
2. Install it on your phone.
3. Open YouTube, tap **Share** -> **More** -> select the **FlashYT** icon, and pick your download quality!

---

## 🔄 How to Update

YouTube changes things often, so keeping FlashYT updated is important! 
- **Windows**: Just download and run the newest `FlashYT-setup.exe` from the Releases page.
- **Mac/Linux**: Run the same Terminal command from Step 1 again.

> **Important**: After updating, go back to `chrome://extensions` and click the little **🔄 Reload** icon on the FlashYT card to refresh the browser button!

---

## 🛠️ Troubleshooting

- **I clicked Download but it says "Host not connected"?**
  The browser lost connection to the background app. Try reloading the extension in `chrome://extensions`. If it persists, just run the installer from Step 1 again!
  
- **Downloads fail with "This video is not available"?**
  YouTube sometimes blocks downloads for Age-Restricted or "YouTube Kids" videos if you aren't signed in. Make sure you are signed into YouTube in your browser and try again!

- **I don't see the Download button?**
  Hard refresh the YouTube page by pressing `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac). Make sure the extension is turned on in `chrome://extensions`.

---

<p align="center">
  <i>Built with ❤️ by <a href="https://www.linkedin.com/in/aazan-noor-khuwaja-cs/">Aazan Noor Khuwaja</a></i><br>
  Released under the MIT License.
</p>
