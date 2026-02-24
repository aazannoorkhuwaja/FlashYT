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

        if (response.type === "pong") {
            hostConnected = true;
            hostNotConnectedFlag = false;
            console.log("Native host connected successfully.");
        }
        else if (response.type === "progress" || response.type === "done" || response.type === "error") {
            // Track active download progress
            if (response.type === "progress" && response.filename) {
                activeDownloads[response.filename] = response;
            }
            if (response.type === "done" || response.type === "error") {
                if (response.filename && activeDownloads[response.filename]) {
                    delete activeDownloads[response.filename];
                }
            }

            // Relays passive streaming events back to all active YouTube tabs
            chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
                tabs.forEach(tab => {
                    chrome.tabs.sendMessage(tab.id, response).catch(() => { });
                });
            });

            // Log history or notify
            if (response.type === "done") {
                chrome.notifications.create({
                    type: "basic",
                    iconUrl: "icons/icon128.png",
                    title: "Download Complete",
                    message: response.filename || "Video saved to Downloads folder."
                });

                // Add to history
                chrome.storage.local.get({ history: [] }, (data) => {
                    let history = data.history;
                    history.unshift({
                        title: response.filename,
                        filename: response.filename,
                        size_mb: response.size_mb,
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
    nativePort.postMessage({ type: "ping" });
}

// Initial connection
connectToHost();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Attempt automatic reconnect if dead
    if (!nativePort) {
        connectToHost();
    }

    if (message.type === "CHECK_STATUS") {
        sendResponse({ status: hostConnected ? "connected" : "disconnected" });
        return true;
    }

    if (hostNotConnectedFlag || !nativePort) {
        sendResponse({ error: "HOST_NOT_CONNECTED" });
        return true;
    }

    if (message.type === "PREFETCH") {
        // Forward PREFETCH call and wait for immediate response
        const listener = (response) => {
            if (response.type === "prefetch_result" || response.type === "error") {
                nativePort.onMessage.removeListener(listener);
                sendResponse(response);
            }
        };
        nativePort.onMessage.addListener(listener);
        nativePort.postMessage({ type: "prefetch", url: message.url });
        return true; // Keeps the sendResponse channel open asynchronously
    }

    if (message.type === "DOWNLOAD") {
        let dummyFileName = `Downloading ${message.title}...`;
        activeDownloads[dummyFileName] = {
            type: "progress",
            filename: dummyFileName,
            percent: "0%",
            eta: "Starting...",
            speed: "0 KiB/s"
        };

        nativePort.postMessage({
            type: "download",
            url: message.url,
            itag: message.itag,
            title: message.title
        });
        sendResponse({ status: "started" });
        return true;
    }

    if (message.type === "OPEN_FOLDER") {
        nativePort.postMessage({ type: "open_folder", path: message.path || "" });
        sendResponse({ status: "ok" });
        return true;
    }

    if (message.type === "GET_HISTORY") {
        chrome.storage.local.get({ history: [] }, (data) => {
            sendResponse({ history: data.history });
        });
        return true;
    }

    if (message.type === "GET_QUEUE") {
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

        activeDownloads[`Quick Context Download`] = {
            type: "progress",
            filename: `Quick Context Download`,
            percent: "0%",
            eta: "Starting...",
            speed: "0 KiB/s"
        };

        nativePort.postMessage({
            type: "download",
            url: url,
            itag: 1080,
            title: "Quick Download"
        });
    }
});
