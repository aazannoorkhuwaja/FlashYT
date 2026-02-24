importScripts("constants.js");

const HOST_NAME = "com.youtube.native.ext";
let nativePort = null;
let hostConnected = false;
let hostNotConnectedFlag = false;

// Cache for active downloads tracking
let activeDownloads = {};

function connectToHost() {
    if (nativePort) return;

    nativePort = chrome.runtime.connectNative(HOST_NAME);

    nativePort.onMessage.addListener((response) => {
        if (!response) return;

        if (response.type === MSG.HOST_PONG) {
            hostConnected = true;
            hostNotConnectedFlag = false;
            console.log("Native host connected successfully.");
        }
        else if (response.type === MSG.HOST_PROGRESS || response.type === MSG.HOST_DONE || response.type === MSG.HOST_ERROR) {
            // Track active download progress keyed by title
            if (response.type === MSG.HOST_PROGRESS && response.title) {
                if (activeDownloads[response.title]) {
                    activeDownloads[response.title].percent = response.percent;
                    activeDownloads[response.title].speed = response.speed;
                    activeDownloads[response.title].eta = response.eta;
                }
            }
            if (response.type === MSG.HOST_DONE || response.type === MSG.HOST_ERROR) {
                if (response.title && activeDownloads[response.title]) {
                    delete activeDownloads[response.title];
                }
            }

            // Relays passive streaming events back to all active YouTube tabs
            chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
                tabs.forEach(tab => {
                    try {
                        chrome.tabs.sendMessage(tab.id, response).catch(() => { });
                    } catch (e) {
                        // Ignore context invalidated errors if the tab was closed/reloaded mid-stream
                    }
                });
            });

            // Log history or notify
            if (response.type === MSG.HOST_DONE) {
                chrome.notifications.create({
                    type: "basic",
                    iconUrl: "icons/icon128.png",
                    title: "Download Complete",
                    message: response.filename || "Video saved to Downloads folder."
                });

                // Grab thumbnail from cache before we delete it (or if it was just deleted, maybe pass it, wait, we deleted it above)
                // Let's rely on the fact that if it's missing we just use a placeholder

                chrome.storage.local.get({ history: [] }, (data) => {
                    let history = data.history;
                    history.unshift({
                        title: response.title || response.filename,
                        filename: response.filename,
                        size_mb: response.size_mb,
                        thumbnail: response.thumbnail || "icons/icon48.png",
                        time: Date.now()
                    });
                    if (history.length > 50) history.pop();
                    chrome.storage.local.set({ history: history });
                });
            }
        }
        else {
            // Unhandled broadcast
            console.log("Received unhandled broadcast from host:", response);
        }
    });

    nativePort.onDisconnect.addListener(() => {
        console.error("Native host disconnected:", chrome.runtime.lastError);
        nativePort = null;
        hostConnected = false;
        hostNotConnectedFlag = true;
        activeDownloads = {}; // Clear queue heavily
    });

    // Test the connection immediately
    nativePort.postMessage({ type: MSG.HOST_PING });
}

// Initial connection
connectToHost();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Attempt automatic reconnect if dead
    if (!nativePort) {
        connectToHost();
    }

    if (message.type === MSG.EXT_CHECK_STATUS) {
        if (!hostConnected && !nativePort) {
            connectToHost();
            // We return "disconnected" quickly, but the background spin-up is already happening now
        }
        sendResponse({ status: hostConnected ? "connected" : "disconnected" });
        return true;
    }

    if (hostNotConnectedFlag || !nativePort) {
        sendResponse({ error: MSG.ERR_NOT_CONNECTED });
        return true;
    }

    if (message.type === MSG.EXT_PREFETCH) {
        // Forward PREFETCH call and wait for immediate response
        const listener = (response) => {
            if (response.type === MSG.HOST_PREFETCH_RESULT || response.type === MSG.HOST_ERROR) {
                nativePort.onMessage.removeListener(listener);
                try {
                    sendResponse(response);
                } catch (e) {
                    console.warn("[YT-Native] Failed to sendResponse to prefetch. Tab may have closed.", e);
                }
            }
        };
        nativePort.onMessage.addListener(listener);
        nativePort.postMessage({ type: MSG.HOST_PREFETCH, url: message.url });
        return true; // Keeps the sendResponse channel open asynchronously
    }

    if (message.type === MSG.EXT_DOWNLOAD) {
        let videoId = "placeholder";
        try {
            videoId = new URL(message.url).searchParams.get("v") || "placeholder";
        } catch (e) {
            console.warn("[YT-Native] Failed to parse YouTube video ID from URL:", message.url, e);
        }
        let thumb = videoId !== "placeholder" ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` : "icons/icon48.png";

        activeDownloads[message.title] = {
            type: MSG.HOST_PROGRESS,
            filename: message.title,
            percent: "0%",
            eta: "Starting...",
            speed: "0 KiB/s",
            thumbnail: thumb
        };

        nativePort.postMessage({
            type: MSG.HOST_DOWNLOAD,
            url: message.url,
            itag: message.itag,
            title: message.title,
            thumbnail: thumb
        });
        sendResponse({ status: "started" });
        return true;
    }

    if (message.type === MSG.EXT_OPEN_FOLDER) {
        nativePort.postMessage({ type: MSG.HOST_OPEN_FOLDER, path: message.path || "" });
        sendResponse({ status: "ok" });
        return true;
    }

    if (message.type === MSG.EXT_UPDATE_ENGINE) {
        activeDownloads["Core Updater"] = {
            type: MSG.HOST_PROGRESS,
            filename: `yt-dlp Core Updater`,
            percent: "0%",
            eta: "Starting...",
            speed: "0 KiB/s",
            thumbnail: "icons/icon48.png"
        };
        nativePort.postMessage({ type: MSG.HOST_UPDATE_ENGINE });
        sendResponse({ status: "ok" });
        return true;
    }

    if (message.type === MSG.EXT_GET_HISTORY) {
        chrome.storage.local.get({ history: [] }, (data) => {
            sendResponse({ history: data.history });
        });
        return true;
    }

    if (message.type === MSG.EXT_GET_QUEUE) {
        sendResponse({ queue: Object.values(activeDownloads) });
        return true;
    }
});

// Setup Context Menu Installer
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "ytdl_native_download",
        title: "Download with YouTube Native Downloader",
        contexts: ["link", "page"],
        documentUrlPatterns: ["*://*.youtube.com/*"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "ytdl_native_download") {
        let url = info.linkUrl || info.pageUrl;
        if (!url || !url.includes("youtube.com/watch")) return;

        if (!nativePort || hostNotConnectedFlag) {
            chrome.notifications.create({
                type: "basic",
                iconUrl: "icons/icon128.png",
                title: "Error",
                message: "Native Desktop App is not running."
            });
            return;
        }

        let videoId = "placeholder";
        try { videoId = new URL(url).searchParams.get("v") || "placeholder"; } catch (e) { }
        let thumb = videoId !== "placeholder" ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` : "icons/icon48.png";

        activeDownloads[`Quick Context Download`] = {
            type: MSG.HOST_PROGRESS,
            filename: `Quick Context Download`,
            percent: "0%",
            eta: "Starting...",
            speed: "0 KiB/s",
            thumbnail: thumb
        };

        nativePort.postMessage({
            type: MSG.HOST_DOWNLOAD,
            url: url,
            itag: 1080,
            title: "Quick Download",
            thumbnail: thumb
        });
    }
});
