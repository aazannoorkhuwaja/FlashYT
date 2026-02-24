const defaultBtnHtml = '⬇ Download';
let isWaitingForMenu = false;
let currentQualities = null;
let currentTitle = null;
let currentUrl = null;

function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 24px;
        background: ${isError ? '#e74c3c' : '#2ecc71'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        z-index: 999999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    document.body.appendChild(toast);
    setTimeout(() => toast.style.opacity = '1', 10);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function injectButton() {
    // YouTube single page architecture protection
    if (document.getElementById('ytdl-native-btn-container')) return;

    let targetContainer = document.querySelector('#owner.ytd-watch-metadata') ||
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
        background-color: rgb(204, 0, 0); 
        color: white; 
        border: none; 
        border-radius: 18px;
        padding: 0 16px; 
        height: 36px; 
        font-weight: 500; 
        font-size: 14px; 
        cursor: pointer;
        display: inline-flex; 
        align-items: center; 
        justify-content: center; 
        flex-shrink: 0; 
        white-space: nowrap;
        transition: background-color 0.2s;
    `;

    btn.onmouseenter = () => { if (btn.style.backgroundColor !== 'rgb(52, 152, 219)') btn.style.backgroundColor = '#a80000'; };
    btn.onmouseleave = () => { if (btn.style.backgroundColor !== 'rgb(52, 152, 219)') btn.style.backgroundColor = 'rgb(204, 0, 0)'; };

    const errorMsg = document.createElement('div');
    errorMsg.id = 'ytdl-error-msg';
    errorMsg.style.cssText = `
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        margin-top: 8px;
        background: #e74c3c;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        width: max-content;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    errorMsg.innerHTML = `Desktop app not running.<br><a href="https://github.com/aazannoorkhuwaja/youtube-native-ext/releases" target="_blank" style="color: white; text-decoration: underline; font-weight: bold;">Download and run the installer first.</a>`;

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
        min-width: 220px;
        overflow: hidden;
    `;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();

        // Ensure host is actually connected BEFORE opening the menu
        chrome.runtime.sendMessage({ type: MSG.EXT_CHECK_STATUS }, (response) => {
            if (response && response.status === "disconnected") {
                errorMsg.style.display = 'block';
                setTimeout(() => errorMsg.style.display = 'none', 5000);
                return;
            }

            if (menu.style.display === 'block') {
                menu.style.display = 'none';
                return;
            }

            menu.style.display = 'block';

            if (currentQualities && currentUrl === window.location.href) {
                buildMenu(currentQualities, currentTitle, currentUrl);
            } else {
                menu.innerHTML = '<div style="padding: 10px 16px; font-size: 14px; color: #aaa; text-align: center;">Fetching qualities...</div>';
                triggerPrefetch(window.location.href);
            }
        });
    });

    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            menu.style.display = 'none';
            errorMsg.style.display = 'none';
        }
    });

    container.appendChild(btn);
    container.appendChild(errorMsg);
    container.appendChild(menu);
    targetContainer.appendChild(container);

    // Explicitly ask for qualities as soon as the DOM generates the button so it is cached
    triggerPrefetch(window.location.href);
}

function buildMenu(qualities, title, urlToDownload) {
    const menu = document.getElementById('ytdl-native-menu');
    const btn = document.getElementById('ytdl-native-btn');
    if (!menu || !btn) return;

    currentQualities = qualities;
    currentTitle = title || "YouTube Video";
    currentUrl = urlToDownload;
    menu.innerHTML = '';

    qualities.forEach(q => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 10px 16px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
            display: flex;
            justify-content: space-between;
        `;
        item.innerHTML = `<span>${q.label}</span> <span style="color: #aaa; font-size: 13px;">${q.size_mb} MB</span>`;

        item.onmouseenter = () => item.style.backgroundColor = '#3f3f3f';
        item.onmouseleave = () => item.style.backgroundColor = 'transparent';

        item.onclick = (e) => {
            e.stopPropagation();
            menu.style.display = 'none';

            btn.textContent = 'Check Queue!';
            btn.style.backgroundColor = '#3498db';
            setTimeout(() => { btn.innerHTML = defaultBtnHtml; btn.style.backgroundColor = 'rgb(204, 0, 0)'; }, 3000);

            chrome.runtime.sendMessage({
                type: MSG.EXT_DOWNLOAD,
                url: urlToDownload,
                itag: q.itag,
                title: currentTitle
            }, (res) => {
                if (res && res.error) {
                    btn.textContent = 'Error!';
                    btn.style.backgroundColor = '#e74c3c';
                    btn.style.cursor = 'pointer';
                    showToast(res.error, true);
                    setTimeout(() => { btn.innerHTML = defaultBtnHtml; btn.style.backgroundColor = 'rgb(204, 0, 0)'; }, 3000);
                }
            });
        };
        menu.appendChild(item);
    });
}

function triggerPrefetch(url) {
    currentQualities = null;

    chrome.runtime.sendMessage({ type: MSG.EXT_PREFETCH, url: url }, (response) => {
        if (!response) {
            console.error("No response from extension background context.");
            return;
        }

        if (response.error === MSG.ERR_NOT_CONNECTED) {
            return;
        }

        if (response.type === MSG.HOST_PREFETCH_RESULT) {
            // Only update the global cache if the user is STILL on the exact same video they requested.
            // This strictly prevents fast-click SPA navigation ghost downloads.
            if (window.location.href === url) {
                currentQualities = response.qualities;
                currentTitle = response.title;
                currentUrl = url;
                const menu = document.getElementById('ytdl-native-menu');
                if (menu && menu.style.display === 'block') {
                    buildMenu(currentQualities, currentTitle, currentUrl);
                }
            }
        } else if (response.type === MSG.HOST_ERROR) {
            const menu = document.getElementById('ytdl-native-menu');
            if (menu && menu.style.display === 'block') {
                menu.innerHTML = `<div style="padding: 10px 16px; font-size: 14px; color: #e74c3c; text-align: center;">⚠ Error: ${response.message}</div>`;
            }
            console.error("Prefetch failed:", response.message);
        }
    });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const btn = document.getElementById('ytdl-native-btn');

    if (message.type === MSG.HOST_DONE) {
        showToast(`Video saved: ${message.filename} `);
    } else if (message.type === MSG.HOST_ERROR) {
        if (btn) {
            btn.textContent = '⚠ Error';
            btn.style.backgroundColor = '#e74c3c';
            btn.style.cursor = 'pointer';
            setTimeout(() => {
                btn.innerHTML = defaultBtnHtml;
                btn.style.backgroundColor = 'rgb(204, 0, 0)';
            }, 3000);
        }
        showToast(message.message || "Download failed.", true);
    }
});

let lastUrl = location.href;
const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (location.href.includes('/watch')) {
            // Clean up old injection if navigating between videos in the SPA
            const oldContainer = document.getElementById('ytdl-native-btn-container');
            if (oldContainer) oldContainer.remove();

            // Wait for target container to re-render using a cheap looping poll
            let retryCount = 0;
            const tryInject = setInterval(() => {
                injectButton();
                if (document.getElementById('ytdl-native-btn-container')) {
                    clearInterval(tryInject);
                    return;
                }
                retryCount++;
                if (retryCount > 10) clearInterval(tryInject);
            }, 500);
        }
    }
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial load check on boot
if (location.href.includes('/watch')) {
    let retryCount = 0;
    const tryInject = setInterval(() => {
        injectButton();
        if (document.getElementById('ytdl-native-btn-container')) {
            clearInterval(tryInject);
        }
        retryCount++;
        if (retryCount > 10) clearInterval(tryInject);
    }, 500);
}
