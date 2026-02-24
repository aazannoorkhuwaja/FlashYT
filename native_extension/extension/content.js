// Utility: Show clean, modern auto-dismissing toast notifications 
function showToast(message, isError = false) {
    let toast = document.getElementById('ytdl-native-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'ytdl-native-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 24px;
            border-radius: 8px;
            color: #ffffff;
            font-family: 'Roboto', sans-serif;
            font-size: 14px;
            font-weight: 500;
            z-index: 9999999;
            transition: opacity 0.3s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            pointer-events: none;
            opacity: 0;
        `;
        document.body.appendChild(toast);
    }

    toast.style.backgroundColor = isError ? '#e74c3c' : '#2ecc71';
    toast.textContent = message;
    toast.style.opacity = '1';

    if (toast.hideTimeout) clearTimeout(toast.hideTimeout);
    toast.hideTimeout = setTimeout(() => {
        toast.style.opacity = '0';
    }, 3500);
}

const defaultBtnHtml = `<svg xmlns="http://www.w3.org/2000/svg" height="20" viewBox="0 0 24 24" width="20" fill="currentColor" style="margin-right: 4px; padding-bottom: 2px;"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>Download`;

let isWaitingForMenu = false;

// Injects the Native Download button into the YouTube player interface
function injectButton() {
    if (document.getElementById('ytdl-native-btn-container')) return;

    // The safest and most horizontally-aligned flex row on YouTube is #owner
    const targetContainer = document.querySelector('#owner.ytd-watch-metadata') ||
        document.querySelector('#top-row.ytd-watch-metadata') ||
        document.querySelector('#menu-container');

    if (!targetContainer) return;

    const container = document.createElement('div');
    container.id = 'ytdl-native-btn-container';
    container.style.cssText = `
        position: relative;
        display: inline-flex;
        margin-left: 12px;
        margin-top: auto;
        margin-bottom: auto;
        font-family: 'Roboto', sans-serif;
    `;

    const btn = document.createElement('button');
    btn.id = 'ytdl-native-btn';
    btn.innerHTML = defaultBtnHtml;
    btn.style.cssText = `
        background-color: #cc0000; color: white; border: none; border-radius: 18px;
        padding: 0 16px; height: 36px; font-weight: 500; font-size: 14px; cursor: pointer;
        display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; white-space: nowrap;
    `;

    const menu = document.createElement('div');
    menu.id = 'ytdl-native-menu';
    menu.style.cssText = `
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        margin-top: 8px;
        background: #282828;
        border: 1px solid #3f3f3f;
        border-radius: 8px;
        padding: 8px 0;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        color: white;
        min-width: 200px;
        overflow: hidden;
    `;

    btn.onclick = (e) => {
        e.stopPropagation();

        // If menu is populated, toggle it
        if (menu.hasChildNodes()) {
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        } else {
            // Still fetching in background...
            isWaitingForMenu = true;
            btn.innerHTML = 'Loading Qualities...';
            btn.style.backgroundColor = '#999999';
            btn.style.cursor = 'wait';
        }
    };

    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            menu.style.display = 'none';
        }
    });

    container.appendChild(btn);
    container.appendChild(menu);
    targetContainer.appendChild(container);

    // Trigger initial background pre-fetch immediately upon injection
    isWaitingForMenu = false;
    chrome.runtime.sendMessage({ action: 'get_formats', url: window.location.href });
}

// YouTube is an SPA; elements load asynchronously. 
// Poll aggressively every 500ms until the Subscribe button appears.
setInterval(injectButton, 500);

// Background pre-fetch tracker for SPA navigation
let currentVideoUrl = '';
setInterval(() => {
    if (window.location.href.includes('watch?v=') && window.location.href !== currentVideoUrl) {
        currentVideoUrl = window.location.href;
        const menu = document.getElementById('ytdl-native-menu');
        const btn = document.getElementById('ytdl-native-btn');
        if (menu) menu.innerHTML = ''; // Clear stale qualities
        if (btn) {
            btn.innerHTML = defaultBtnHtml;
            btn.style.backgroundColor = '#cc0000';
            btn.style.cursor = 'pointer';
        }
        // Silently pre-fetch for the new video
        isWaitingForMenu = false;
        chrome.runtime.sendMessage({ action: 'get_formats', url: currentVideoUrl });
    }
}, 1000);

// Listen for incoming responses/updates relayed from the Python Host via background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const btn = document.getElementById('ytdl-native-btn');
    const menu = document.getElementById('ytdl-native-menu');

    if (message.action === 'formats_ready') {
        if (btn && btn.innerHTML.includes('Loading Qualities')) {
            btn.innerHTML = defaultBtnHtml;
            btn.style.backgroundColor = '#cc0000';
            btn.style.cursor = 'pointer';
        }

        if (menu && message.qualities) {
            menu.innerHTML = ''; // Clear previous
            message.qualities.forEach(q => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 10px 16px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.2s;
                    display: flex;
                    justify-content: space-between;
                `;
                item.innerHTML = `<span>${q.label}</span> <span style="color: #aaa; font-size: 13px;">${q.size}</span>`;

                item.onmouseenter = () => item.style.backgroundColor = '#3f3f3f';
                item.onmouseleave = () => item.style.backgroundColor = 'transparent';

                item.onclick = (e) => {
                    e.stopPropagation();
                    menu.style.display = 'none';

                    // INSTANT UI FEEDBACK (No 'Starting...' wait)
                    if (btn) {
                        btn.textContent = '0.0% (Connecting...)';
                        btn.style.backgroundColor = '#3498db';
                        btn.style.cursor = 'progress';
                    }
                    showToast(`Starting download: ${q.label}`);
                    chrome.runtime.sendMessage({
                        action: 'download',
                        url: window.location.href,
                        format: q.format
                    });
                };
                menu.appendChild(item);
            });
            // If user clicked while loading, pop it open now
            if (isWaitingForMenu) {
                menu.style.display = 'block';
                isWaitingForMenu = false;
            }
        }

    } else if (message.action === 'download_progress') {
        // Update button text with live percentage and speed piped directly from yt-dlp
        if (btn) {
            btn.textContent = `${message.percent} (${message.speed})`;
            btn.style.backgroundColor = '#3498db';
            btn.style.cursor = 'progress';
        }

    } else if (message.action === 'download_finished') {
        if (btn) {
            btn.textContent = 'Complete!';
            btn.style.backgroundColor = '#2ecc71';
            btn.style.cursor = 'pointer';
            setTimeout(() => {
                btn.innerHTML = defaultBtnHtml;
                btn.style.backgroundColor = '#cc0000';
            }, 3000);
        }
        showToast(`Download complete: ${message.filename}`);

    } else if (message.action === 'error') {
        if (btn) {
            btn.textContent = 'Error!';
            btn.style.backgroundColor = '#e74c3c';
            btn.style.cursor = 'pointer';
            setTimeout(() => {
                btn.innerHTML = defaultBtnHtml;
                btn.style.backgroundColor = '#cc0000';
            }, 3000);
        }
        showToast(`Backend Error: ${message.error}`, true);
    }
});
