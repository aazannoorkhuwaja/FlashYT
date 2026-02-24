// This script bridges the Chrome Extension's Content Script with our Python Host.

let nativePort = null;

function connectToNativeHost() {
    console.log("[Background] Connecting to native host: com.aazan.ytdl");
    nativePort = chrome.runtime.connectNative('com.aazan.ytdl');

    nativePort.onMessage.addListener((message) => {
        console.log("[Background] Received message from Python host:", message);
        // Relay the message back to ALL YouTube tabs robustly
        chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
            for (const tab of tabs) {
                chrome.tabs.sendMessage(tab.id, message);
            }
        });
    });

    nativePort.onDisconnect.addListener(() => {
        const errorMsg = chrome.runtime.lastError ? chrome.runtime.lastError.message : "Disconnected silently";
        console.error("[Background] Disconnected from native host.", errorMsg);
        nativePort = null;

        // Alert all YouTube tabs immediately so the button unlocks from "Fetching..."
        chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
            for (const tab of tabs) {
                chrome.tabs.sendMessage(tab.id, {
                    action: "error",
                    error: "Host Disconnected: " + errorMsg
                });
            }
        });
    });
}

// Establish the connection immediately when the service worker wakes up
connectToNativeHost();

// Listen for messages coming from content.js (the YouTube page)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("[Background] Received request from content script:", request);

    // Ensure the native port is alive before sending
    if (!nativePort) {
        connectToNativeHost();
    }

    if (nativePort) {
        nativePort.postMessage(request);
    } else {
        console.error("[Background] Failed to connect to native port. Message dropped.");
    }

    return true; // Keep the message channel open
});
