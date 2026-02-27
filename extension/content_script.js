const defaultBtnHtml = '<span class="ytdl-btn-text">Download</span>';
let currentQualities = null;
let isModalOpen = false;
let currentVideoId = null;
let isPrefetching = false;
let currentDownloadId = null;
let lastPrefetchError = '';

function getVideoId() {
    const url = window.location.href;
    const match = url.match(/(?:\/v\/|v=|vi\/|vi=|\/embed\/|\/shorts\/|\/live\/|youtu\.be\/|\/v=|^)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
}

function showToast(message, isError = false, duration = 4000) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.className = 'flashyt-toast ' + (isError ? 'flashyt-toast-error' : 'flashyt-toast-success');
    document.body.appendChild(toast);

    setTimeout(() => { toast.classList.add('show'); }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

function safeSendMessage(message, callback) {
    try {
        chrome.runtime.sendMessage(message, callback);
    } catch (e) {
        if (e.message.includes("Extension context invalidated")) {
            closeModal();
            showToast("Extension updated! Please refresh this YouTube page.", true);
        } else {
            console.error("[FlashYT] SendMessage error:", e);
        }
    }
}

function createModal() {
    if (document.getElementById('flashyt-modal-overlay')) return document.getElementById('flashyt-modal-overlay');

    const overlay = document.createElement('div');
    overlay.id = 'flashyt-modal-overlay';
    overlay.className = 'flashyt-overlay';

    const modal = document.createElement('div');
    modal.id = 'flashyt-modal';
    modal.className = 'flashyt-modal';

    const header = document.createElement('div');
    header.className = 'flashyt-modal-header';
    header.innerHTML =
        '<h2 class="flashyt-modal-title">Select Quality</h2>' +
        '<div class="flashyt-header-actions">' +
        '    <button id="flashyt-modal-refresh" class="flashyt-action-icon-btn" title="Refresh Qualities">' +
        '        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>' +
        '    </button>' +
        '    <button id="flashyt-modal-close" class="flashyt-close-btn">' +
        '        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>' +
        '    </button>' +
        '</div>';

    const content = document.createElement('div');
    content.id = 'flashyt-modal-content';
    content.className = 'flashyt-modal-content';

    modal.appendChild(header);
    modal.appendChild(content);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    overlay.onclick = (e) => {
        if (e.target === overlay) closeModal();
    };

    document.getElementById('flashyt-modal-close').onclick = closeModal;
    document.getElementById('flashyt-modal-refresh').onclick = (e) => {
        e.stopPropagation();
        triggerPrefetch(window.location.href, true);
    };
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isModalOpen) closeModal();
    });

    return overlay;
}

function openModal() {
    const overlay = createModal();
    const modal = document.getElementById('flashyt-modal');

    isModalOpen = true;
    overlay.style.display = 'flex';
    void overlay.offsetWidth; // trigger reflow
    overlay.style.opacity = '1';
    modal.style.transform = 'scale(1)';

    renderModalContent();

    safeSendMessage({ type: "CHECK_STATUS" }, (response) => {
        if (response && response.status === "disconnected") {
            closeModal();
            showToast("FlashYT desktop app not running. Run the installer first.", true);
        }
    });
}

function closeModal() {
    const overlay = document.getElementById('flashyt-modal-overlay');
    if (!overlay) return;
    const modal = document.getElementById('flashyt-modal');

    isModalOpen = false;
    overlay.style.opacity = '0';
    modal.style.transform = 'scale(0.95)';
    setTimeout(() => {
        if (!isModalOpen) overlay.style.display = 'none';
    }, 300);
}

function renderModalContent() {
    const content = document.getElementById('flashyt-modal-content');
    if (!content) return;

    if (!currentQualities) {
        if (lastPrefetchError) {
            content.innerHTML =
                '<div class="flashyt-loading-header">' +
                '    <div class="flashyt-loading-title">Could Not Fetch Streams</div>' +
                '    <div class="flashyt-loading-subtitle">' + lastPrefetchError + '</div>' +
                '</div>';
            return;
        }
        content.innerHTML =
            '<div class="flashyt-loading-header">' +
            '    <div class="flashyt-loading-title">Fetching Premium Streams</div>' +
            '    <div class="flashyt-loading-subtitle">Contacting servers...</div>' +
            '</div>' +
            '<div class="flashyt-skeleton mb"></div>' +
            '<div class="flashyt-skeleton mb d1"></div>' +
            '<div class="flashyt-skeleton d2"></div>';
        return;
    }

    content.innerHTML = '';
    const videoId = getVideoId();
    const title = document.title.replace('- YouTube', '').trim();

    currentQualities.forEach(q => {
        const item = document.createElement('button');
        item.className = 'flashyt-quality-item';

        item.innerHTML =
            '<span class="flashyt-quality-label">' + q.label + '</span>' +
            '<span class="flashyt-quality-size">' + q.size_mb + ' MB</span>';

        item.onclick = () => {
            closeModal();
            startDownload(q, title, videoId);
        };

        content.appendChild(item);
    });
}



function startDownload(qualityObj, title, videoId) {
    const btn = document.getElementById('ytdl-native-btn');
    if (btn) {
        btn.textContent = 'Starting... (0%)';
        btn.style.backgroundColor = '#3498db';
        btn.style.borderColor = 'rgba(255,0,0,1)';
        btn.style.boxShadow = '0 0 16px rgba(255,0,0,0.7)';
        btn.style.cursor = 'progress';
        btn.dataset.state = 'busy';
    }

    // Generate valid thumbnail for background.js
    const thumbnail = `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`;
    currentDownloadId = 'dl_' + Date.now();

    safeSendMessage({
        type: 'DOWNLOAD',
        url: window.location.href,
        itag: qualityObj.itag,
        real_itag: qualityObj.real_itag,
        title: title,
        videoId: videoId,
        downloadId: currentDownloadId,
        size_mb: qualityObj.size_mb,
        thumbnail: thumbnail,
        format: qualityObj.label
    }, (res) => {
        if (res && res.error) {
            if (btn) {
                btn.textContent = 'Error!';
                btn.style.backgroundColor = '#e74c3c';
                btn.style.cursor = 'pointer';
                btn.dataset.state = 'idle';
                setTimeout(() => { btn.innerHTML = defaultBtnHtml; btn.style.backgroundColor = 'rgb(204,0,0)'; }, 3000);
            }
            showToast(res.error, true);
        } else {
            showToast("Download added to queue.");
        }
    });
}

function injectButton() {
    if (document.getElementById('ytdl-native-btn-container')) return;

    let targetContainer = document.querySelector('#owner.ytd-watch-metadata') ||
        document.querySelector('#top-row.ytd-watch-metadata') ||
        document.querySelector('#menu-container');
    if (!targetContainer) return;

    const container = document.createElement('div');
    container.id = 'ytdl-native-btn-container';
    container.style.cssText =
        'position:relative;display:inline-flex;margin-left:12px;' +
        'margin-top:auto;margin-bottom:auto;font-family:"Inter",Roboto,sans-serif;';

    const btn = document.createElement('button');
    btn.id = 'ytdl-native-btn';
    btn.innerHTML = defaultBtnHtml;
    btn.dataset.state = 'idle';
    btn.style.cssText =
        'background-color:rgb(204,0,0);color:white;border:1px solid transparent;border-radius:18px;' +
        'padding:0 16px;height:36px;font-weight:600;font-size:14px;cursor:pointer;' +
        'display:inline-flex;align-items:center;justify-content:center;' +
        'flex-shrink:0;white-space:nowrap;transition:all 0.2s;';

    btn.onmouseenter = () => { if (btn.dataset.state === 'idle') { btn.style.backgroundColor = '#a80000'; } };
    btn.onmouseleave = () => { if (btn.dataset.state === 'idle') { btn.style.backgroundColor = 'rgb(204,0,0)'; } };

    btn.onclick = (e) => {
        e.stopPropagation();

        // 1. Prevent action if already downloading
        if (btn.dataset.state === 'busy') {
            showToast("Download already in progress...");
            return;
        }

        // Anti-spam throttle (300ms)
        const now = Date.now();
        if (btn.dataset.lastClick && now - parseInt(btn.dataset.lastClick) < 300) return;
        btn.dataset.lastClick = now;

        if (!currentQualities) {
            openModal();
            // Fallback: if passive prefetch hasn't finished or started for some reason, trigger again.
            if (!isPrefetching) {
                triggerPrefetch(window.location.href, true);
            }
        } else {
            openModal();
        }
    };

    container.appendChild(btn);
    targetContainer.appendChild(container);

    const newVideoId = getVideoId();
    if (newVideoId && currentVideoId !== newVideoId) {
        currentQualities = null;
        currentVideoId = newVideoId;
        // UX 1: Passive Prefetching on Page Load
        triggerPrefetch(window.location.href);
    }
}

function triggerPrefetch(url, force = false) {
    currentQualities = null;
    lastPrefetchError = '';
    isPrefetching = true;
    if (isModalOpen) renderModalContent();

    const btn = document.getElementById('ytdl-native-btn');
    if (btn) {
        btn.innerHTML = defaultBtnHtml;
        btn.style.backgroundColor = 'rgb(204,0,0)';
        btn.style.borderColor = 'transparent';
        btn.style.boxShadow = 'none';
        btn.style.cursor = 'pointer';
        btn.dataset.state = 'idle';
    }

    safeSendMessage({ type: "PREFETCH", url, force }, (response) => {
        isPrefetching = false;
        if (!response) {
            return;
        }
        if (response.error === "HOST_NOT_CONNECTED") {
            return;
        }
        if (response.type === "prefetch_result") {
            currentQualities = response.qualities;
            lastPrefetchError = '';
            if (response.warning) {
                showToast(response.warning, true, 5000);
            }
            if (isModalOpen) renderModalContent();
        } else if (response.type === "error") {
            lastPrefetchError = response.message || "Failed to fetch qualities.";
            if (isModalOpen) renderModalContent();
            else showToast("Failed to fetch qualities: " + lastPrefetchError, true);
        }
    });
}

chrome.runtime.onMessage.addListener((message) => {
    // Only process if it matches our current video
    if (message.videoId && message.videoId !== getVideoId()) return;

    if (message.type === 'HOST_NOT_INSTALLED') {
        showToast(
            '⚡ FlashYT: Desktop host not installed. Download the installer from GitHub.',
            true,
            8000
        );
        return;
    }

    const btn = document.getElementById('ytdl-native-btn');
    if (!btn) return;

    if (message.type === 'progress') {
        if (message.downloadId && message.downloadId !== currentDownloadId) return;
        const speedStr = message.speed ? ' (' + message.speed + ')' : '';
        btn.textContent = message.percent + speedStr;
        btn.style.backgroundColor = '#3498db';
        btn.style.borderColor = 'rgba(250,204,21,1)';
        btn.style.boxShadow = '0 0 16px rgba(250,204,21,0.8)';
        btn.style.cursor = 'progress';
        btn.dataset.state = 'busy';
    } else if (message.type === 'control_ack' || message.type === 'paused') {
        const action = message.type === 'paused' ? 'pause' : message.action;
        if (message.downloadId && message.downloadId !== currentDownloadId) return;
        if (message.type === 'control_ack' && !message.ok) {
            showToast(message.message || "Action failed.", true);
            return;
        }

        if (action === 'pause') {
            if (message.type === 'paused') {
                btn.textContent = 'Paused';
                btn.style.backgroundColor = '#f59e0b';
                btn.style.borderColor = 'rgba(250,204,21,0.6)';
                btn.style.boxShadow = '0 0 8px rgba(250,204,21,0.25)';
                btn.style.cursor = 'pointer';
                btn.dataset.state = 'paused';
            } else {
                btn.textContent = 'Pausing...';
                btn.style.backgroundColor = '#f59e0b';
                btn.style.borderColor = 'rgba(250,204,21,1)';
                btn.style.boxShadow = '0 0 12px rgba(250,204,21,0.5)';
                btn.style.cursor = 'progress';
                btn.dataset.state = 'busy';
            }
        } else if (action === 'resume') {
            btn.textContent = 'Resuming...';
            btn.style.backgroundColor = '#3498db';
            btn.style.borderColor = 'rgba(250,204,21,1)';
            btn.style.boxShadow = '0 0 16px rgba(250,204,21,0.8)';
            btn.style.cursor = 'progress';
            btn.dataset.state = 'busy';
        } else if (action === 'cancel') {
            currentDownloadId = null;
            btn.innerHTML = defaultBtnHtml;
            btn.style.backgroundColor = 'rgb(204,0,0)';
            btn.style.borderColor = 'transparent';
            btn.style.boxShadow = 'none';
            btn.style.cursor = 'pointer';
            btn.dataset.state = 'idle';
            showToast("Download cancelled.");
        }
    } else if (message.type === 'done') {
        if (message.downloadId && message.downloadId !== currentDownloadId) return;
        currentDownloadId = null;
        btn.textContent = message.already_exists ? '\u2713 Already Downloaded' : '\u2713 Saved';
        btn.style.backgroundColor = '#10b981'; // emerald
        btn.style.borderColor = 'rgba(250,204,21,0.5)';
        btn.style.boxShadow = '0 0 8px rgba(250,204,21,0.2)';
        btn.style.cursor = 'pointer';
        btn.dataset.state = 'idle';
        setTimeout(() => {
            btn.innerHTML = defaultBtnHtml;
            btn.style.backgroundColor = 'rgb(204,0,0)';
        }, 3000);
    } else if (message.type === 'error') {
        if (message.downloadId && message.downloadId !== currentDownloadId) return;
        currentDownloadId = null;
        btn.textContent = '\u26A0 Error';
        btn.style.backgroundColor = '#ef4444'; // red
        btn.style.borderColor = 'rgba(250,204,21,0.5)';
        btn.style.boxShadow = '0 0 8px rgba(250,204,21,0.2)';
        btn.style.cursor = 'pointer';
        btn.dataset.state = 'idle';
        setTimeout(() => {
            btn.innerHTML = defaultBtnHtml;
            btn.style.backgroundColor = 'rgb(204,0,0)';
        }, 3000);
        showToast(message.message || "Download failed.", true);
    } else if (message.type === 'cancelled') {
        if (message.downloadId && message.downloadId !== currentDownloadId) return;
        currentDownloadId = null;
        btn.innerHTML = defaultBtnHtml;
        btn.style.backgroundColor = 'rgb(204,0,0)';
        btn.style.borderColor = 'transparent';
        btn.style.boxShadow = 'none';
        btn.style.cursor = 'pointer';
        btn.dataset.state = 'idle';
        showToast("Download cancelled.");
    }
});

let lastUrl = location.href;
let observerDebounce = null;
const observer = new MutationObserver(() => {
    if (observerDebounce) clearTimeout(observerDebounce);
    observerDebounce = setTimeout(() => {
        // 1) React to URL changes (SPA navigation)
        if (location.href !== lastUrl) {
            lastUrl = location.href;
            closeModal(); // 3A: Prevent SPA Modal Zombie
            currentQualities = null;
            if (location.href.includes('/watch')) {
                const old = document.getElementById('ytdl-native-btn-container');
                if (old) old.remove(); // Force a clean slate on new video
            }
        }

        // 2) Always attempt to inject if we are on a watch page.
        // injectButton() handles deduplication natively.
        if (location.href.includes('/watch')) {
            injectButton();
        }
    }, 100);
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial attempt for good measure
if (location.href.includes('/watch')) {
    injectButton();
}
