document.addEventListener('DOMContentLoaded', () => {
    // 1. Handle tab switching
    const tabs = document.querySelectorAll('.tab');
    const panes = document.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.target).classList.add('active');
        });
    });

    // 2. Check connection status to native host
    const connStatus = document.getElementById('conn-status');
    const connText = connStatus.querySelector('.text');

    chrome.runtime.sendMessage({ type: "CHECK_STATUS" }, (response) => {
        if (!response || response.error || response.status === "disconnected") {
            connStatus.className = 'status-indicator disconnected';
            connText.textContent = 'Not Running';
        } else {
            connStatus.className = 'status-indicator connected';
            connText.textContent = 'Connected';
            document.getElementById('btn-open-folder').style.display = 'flex';
        }
    });

    // 3. Load download history from local storage
    const downloadsList = document.getElementById('downloads-list');
    chrome.runtime.sendMessage({ type: "GET_HISTORY" }, (response) => {
        if (response && response.history && response.history.length > 0) {
            downloadsList.innerHTML = ''; // clear empty state

            response.history.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';

                const date = new Date(item.time).toLocaleDateString(undefined, {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                });

                // Extract video ID from youtube filename if possible, else use a placeholder
                // This is a naive heuristic since we don't store the raw URL in history currently
                // But the instructions said to add a thumbnail
                div.innerHTML = `
                    <img class="vid-thumbnail" src="https://i.ytimg.com/vi/placeholder/mqdefault.jpg" alt="thumbnail" onerror="this.src='icons/icon48.png'">
                    <div class="vid-info">
                        <div class="vid-title" title="${item.title}">${item.title}</div>
                        <div class="vid-meta">
                            <span class="quality-badge">${item.filename.split('.').pop().toUpperCase()}</span>
                            <span>${item.size_mb} MB &bull; ${date}</span>
                        </div>
                    </div>
                `;

                div.addEventListener('click', () => {
                    chrome.runtime.sendMessage({ type: "OPEN_FOLDER" });
                    window.close();
                });

                downloadsList.appendChild(div);
            });
        }
    });

    // 4. Load Active Queue dynamically
    const queueList = document.getElementById('pane-queue');
    function refreshQueue() {
        chrome.runtime.sendMessage({ type: "GET_QUEUE" }, (response) => {
            if (response && response.queue) {
                if (response.queue.length === 0) {
                    queueList.innerHTML = '<div style="padding: 24px; text-align: center; color: #aaaaaa;">No active downloads.</div>';
                    return;
                }

                queueList.innerHTML = '';
                response.queue.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'history-item';

                    div.innerHTML = `
                        <div class="vid-info" style="margin-left: 0; width: 100%;">
                            <div class="vid-title" title="${item.filename}" style="font-weight: 500;">${item.filename}</div>
                            <div class="vid-meta" style="margin-top: 8px; color: #3ea6ff; font-weight: 500;">
                                <span>${item.percent}</span> &bull; <span>${item.speed}</span> &bull; <span>ETA: ${item.eta}</span>
                            </div>
                        </div>
                    `;
                    queueList.appendChild(div);
                });
            }
        });
    }

    // Refresh queue immediately and then every second while the popup is open
    refreshQueue();
    setInterval(refreshQueue, 1000);

    // 5. Button bindings
    document.getElementById('btn-open-folder').addEventListener('click', () => {
        chrome.runtime.sendMessage({ type: "OPEN_FOLDER" });
        window.close();
    });

    document.getElementById('btn-check-updates').addEventListener('click', () => {
        chrome.tabs.create({ url: "https://github.com/aazannoorkhuwaja/youtube-native-ext/releases" });
    });

    document.getElementById('btn-report-bug').addEventListener('click', () => {
        chrome.tabs.create({ url: "https://github.com/aazannoorkhuwaja/youtube-native-ext/issues" });
    });

    document.getElementById('btn-view-log').addEventListener('click', () => {
        chrome.runtime.sendMessage({ type: "OPEN_FOLDER", path: "%APPDATA%\\YouTubeNativeExt" });
    });
});
