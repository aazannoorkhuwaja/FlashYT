// ==UserScript==
// @name         One-Click YouTube Downloader
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Adds a download button to YouTube videos that communicates with a local Flask server to trigger downloads.
// @author       Aazan Noor Khuwaja
// @match        *://*.youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @updateURL    https://raw.githubusercontent.com/aazannoorkhuwaja/one_click_ytmp4_download/main/userscript.js
// @downloadURL  https://raw.githubusercontent.com/aazannoorkhuwaja/one_click_ytmp4_download/main/userscript.js
// ==/UserScript==

(function () {
    'use strict';

    const SERVER_URL = 'http://127.0.0.1:5000/download';
    const STATUS_URL = 'http://127.0.0.1:5000/status';
    const CONFIG_URL = 'http://127.0.0.1:5000/config';
    const BROWSE_URL = 'http://127.0.0.1:5000/browse';
    const PROGRESS_URL = 'http://127.0.0.1:5000/progress';

    // =============== DOWNLOAD LOGIC ===============

    function pollStatus(btn, jobId) {
        if (btn._pollingInterval) clearInterval(btn._pollingInterval);

        const spanElement = btn.querySelector('span');
        const originalText = 'Download'; // Always reset to 'Download'

        btn._pollingInterval = setInterval(() => {
            GM_xmlhttpRequest({
                method: "GET",
                url: `${STATUS_URL}/${jobId}`,
                onload: function (response) {
                    try {
                        const res = JSON.parse(response.responseText);

                        if (res.status === 'starting') {
                            if (spanElement) spanElement.textContent = 'Starting...';
                        } else if (res.status === 'downloading') {
                            if (spanElement) spanElement.textContent = `Downloading ${res.percent} (${res.speed})`;
                        } else if (res.status === 'processing') {
                            if (spanElement) spanElement.textContent = 'Merging...';
                            btn.style.backgroundColor = '#f39c12';
                        } else if (res.status === 'finished') {
                            clearInterval(btn._pollingInterval);
                            if (spanElement) spanElement.textContent = 'Complete!';
                            btn.style.backgroundColor = '#2ecc71';
                            btn.style.cursor = 'default';

                            setTimeout(() => {
                                if (spanElement) spanElement.textContent = originalText;
                                btn.disabled = false;
                                btn.style.backgroundColor = '#cc0000';
                                btn.style.cursor = 'pointer';
                            }, 5000);

                        } else if (res.status === 'error') {
                            clearInterval(btn._pollingInterval);
                            if (spanElement) spanElement.textContent = 'Error!';
                            btn.style.backgroundColor = '#e74c3c';
                            console.error("Download Error:", res.error);
                            alert("Download Failed: " + res.error);

                            setTimeout(() => {
                                if (spanElement) spanElement.textContent = originalText;
                                btn.disabled = false;
                                btn.style.backgroundColor = '#cc0000';
                                btn.style.cursor = 'pointer';
                            }, 3000);
                        }
                    } catch (e) {
                        console.error("Failed to parse status response", e);
                        // Stop polling and reset if we get dead HTML/404s
                        clearInterval(btn._pollingInterval);
                        if (spanElement) spanElement.textContent = 'Error!';
                        btn.style.backgroundColor = '#e74c3c';
                        setTimeout(() => {
                            if (spanElement) spanElement.textContent = originalText;
                            btn.disabled = false;
                            btn.style.backgroundColor = '#cc0000';
                            btn.style.cursor = 'pointer';
                        }, 3000);
                    }
                }
            });
        }, 1000);
    }

    function createDownloadButton() {
        const btn = document.createElement('button');
        btn.id = 'yt-downloader-btn';

        btn.style.backgroundColor = '#cc0000';
        btn.style.color = '#ffffff';
        btn.style.border = 'none';
        btn.style.borderRadius = '18px';
        btn.style.padding = '0 16px';
        btn.style.height = '36px';
        btn.style.fontSize = '14px';
        btn.style.fontWeight = '500';
        btn.style.cursor = 'pointer';
        btn.style.marginLeft = '8px';
        btn.style.fontFamily = 'Roboto, Arial, sans-serif';
        btn.style.display = 'flex';
        btn.style.alignItems = 'center';
        btn.style.justifyContent = 'center';

        // Fix TrustedTypes Error by using Native DOM Elements instead of innerHTML
        const svgNS = "http://www.w3.org/2000/svg";
        const svgIcon = document.createElementNS(svgNS, "svg");
        svgIcon.setAttribute("style", "width: 16px; height: 16px; margin-right: 6px; fill: currentColor;");
        svgIcon.setAttribute("viewBox", "0 0 24 24");
        const svgPath = document.createElementNS(svgNS, "path");
        svgPath.setAttribute("d", "M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z");
        svgIcon.appendChild(svgPath);

        const spanElement = document.createElement('span');
        spanElement.textContent = "Download";

        btn.appendChild(svgIcon);
        btn.appendChild(spanElement);

        btn.addEventListener('mouseenter', () => {
            if (!btn.disabled) btn.style.backgroundColor = '#ff0000';
        });
        btn.addEventListener('mouseleave', () => {
            if (!btn.disabled) btn.style.backgroundColor = '#cc0000';
        });

        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            const videoUrl = window.location.href;

            if (spanElement) spanElement.textContent = 'Checking config...';
            btn.disabled = true;
            btn.style.backgroundColor = '#999999';
            btn.style.cursor = 'wait';

            function initiateQualities() {
                if (prefetchCache.status === 'done' && prefetchCache.url === videoUrl) {
                    if (spanElement) spanElement.textContent = 'Download';
                    btn.disabled = false;
                    btn.style.backgroundColor = '#cc0000';
                    btn.style.cursor = 'pointer';
                    showQualityModal(videoUrl, prefetchCache.data.formats, prefetchCache.data.audio_only);
                } else if (prefetchCache.status === 'fetching' && prefetchCache.url === videoUrl) {
                    if (spanElement) spanElement.textContent = 'Waiting for qualities...';
                    // Re-check every 500ms until done
                    setTimeout(initiateQualities, 500);
                } else {
                    // Fallback to fetch directly
                    fetchFormatsFallback(videoUrl);
                }
            }

            // Check config for first-time folder setup
            GM_xmlhttpRequest({
                method: "GET",
                url: CONFIG_URL,
                onload: function (response) {
                    try {
                        const config = JSON.parse(response.responseText);
                        if (!config.download_dir) {
                            if (spanElement) spanElement.textContent = 'Select Folder...';
                            GM_xmlhttpRequest({
                                method: "POST",
                                url: 'http://127.0.0.1:5000/choose_folder',
                                onload: function (res2) {
                                    const result2 = JSON.parse(res2.responseText);
                                    if (result2.status === 'success') {
                                        initiateQualities();
                                    } else {
                                        resetBtnError('Cancelled. A download folder is required!');
                                    }
                                },
                                onerror: () => resetBtnError('Failed to open folder picker.')
                            });
                        } else {
                            initiateQualities();
                        }
                    } catch (e) {
                        initiateQualities(); // Fallback
                    }
                },
                onerror: () => resetBtnError('Error connecting to local server. Make sure the Python Flask app is running at ' + SERVER_URL)
            });

            function formatBytes(bytes) {
                if (bytes === 0) return '0 B';
                const k = 1024;
                const sizes = ['B', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
            }

            function fetchFormatsFallback(url) {
                if (spanElement) spanElement.textContent = 'Fetching Qualities...';
                GM_xmlhttpRequest({
                    method: "POST",
                    url: 'http://127.0.0.1:5000/get_formats',
                    headers: { "Content-Type": "application/json" },
                    data: JSON.stringify({ url: url }),
                    onload: function (res) {
                        try {
                            const result = JSON.parse(res.responseText);
                            if (result.status === 'success') {
                                if (spanElement) spanElement.textContent = 'Download';
                                btn.disabled = false;
                                btn.style.backgroundColor = '#cc0000';
                                btn.style.cursor = 'pointer';
                                showQualityModal(url, result.formats, result.audio_only);
                            } else {
                                resetBtnError('Error fetching formats: ' + (result.error || 'Unknown'));
                            }
                        } catch (e) {
                            resetBtnError('Failed to parse formats.');
                        }
                    },
                    onerror: () => resetBtnError('Server is down. Cannot fetch formats.')
                });
            }

            function showQualityModal(url, formats, audioOnly) {
                const backdrop = document.createElement('div');
                backdrop.style.cssText = `
                    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.6); z-index: 999999;
                    display: flex; justify-content: center; align-items: center;
                    backdrop-filter: blur(4px); font-family: 'Roboto', sans-serif;
                `;

                const modal = document.createElement('div');
                modal.style.cssText = `
                    background: #181818; border-radius: 16px; padding: 24px;
                    width: 340px; border: 1px solid #333; color: white;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.8);
                `;

                const title = document.createElement('h3');
                title.textContent = 'Select Quality';
                title.style.cssText = 'margin: 0 0 16px 0; font-size: 18px; text-align: center; border-bottom: 1px solid #333; padding-bottom: 12px;';
                modal.appendChild(title);

                const list = document.createElement('div');
                list.style.cssText = 'display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto; padding-right: 4px;';

                function createOption(label, sizeBytes, selectionKey) {
                    const opt = document.createElement('button');
                    opt.style.cssText = `
                        background: #272727; border: 1px solid #444; border-radius: 8px;
                        padding: 12px 16px; color: white; display: flex;
                        justify-content: space-between; align-items: center; cursor: pointer;
                        transition: all 0.2s; font-size: 14px;
                    `;
                    opt.addEventListener('mouseenter', () => opt.style.background = '#3f3f3f');
                    opt.addEventListener('mouseleave', () => opt.style.background = '#272727');

                    const leftSpan = document.createElement('span');
                    leftSpan.textContent = label;
                    leftSpan.style.fontWeight = '600';

                    const rightSpan = document.createElement('span');
                    rightSpan.textContent = formatBytes(sizeBytes || 0);
                    rightSpan.style.color = '#aaa';
                    rightSpan.style.fontSize = '12px';

                    opt.appendChild(leftSpan);
                    opt.appendChild(rightSpan);

                    opt.addEventListener('click', () => {
                        document.body.removeChild(backdrop);
                        // We only send a simple key like "video_1080" or "audio_only".
                        // The Python backend converts this into a safe format string
                        // with fallbacks, so users never see "requested format not available".
                        triggerDownload(url, selectionKey);
                    });
                    return opt;
                }

                if (formats && formats.length > 0) {
                    formats.forEach(f => {
                        const key = `video_${f.height || parseInt((f.resolution || '0').replace('p', ''), 10) || 0}`;
                        list.appendChild(createOption(f.resolution + ' (MP4)', f.size_bytes, key));
                    });
                } else {
                    const fallback = document.createElement('div');
                    fallback.textContent = 'No known video formats found.';
                    fallback.style.cssText = 'color: #aaa; text-align: center; font-size: 13px; margin-bottom: 8px;';
                    list.appendChild(fallback);
                }

                if (audioOnly) {
                    const divArea = document.createElement('div');
                    divArea.style.cssText = 'height: 1px; background: #333; margin: 8px 0;';
                    list.appendChild(divArea);
                    list.appendChild(createOption('Audio Only (M4A)', audioOnly.size_bytes, 'audio_only'));
                }

                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = 'Cancel';
                cancelBtn.style.cssText = `
                    background: transparent; border: none; color: #888;
                    width: 100%; padding: 12px; margin-top: 12px; cursor: pointer;
                    font-size: 14px; border-radius: 8px;
                `;
                cancelBtn.addEventListener('mouseenter', () => cancelBtn.style.color = 'white');
                cancelBtn.addEventListener('mouseleave', () => cancelBtn.style.color = '#888');
                cancelBtn.addEventListener('click', () => {
                    document.body.removeChild(backdrop);
                    resetBtnError();
                });

                modal.appendChild(list);
                modal.appendChild(cancelBtn);
                backdrop.appendChild(modal);
                document.body.appendChild(backdrop);
            }

            function resetBtnError(msg) {
                if (spanElement) spanElement.textContent = 'Download';
                btn.disabled = false;
                btn.style.backgroundColor = '#cc0000';
                btn.style.cursor = 'pointer';
                if (msg) alert(msg);
            }

            function triggerDownload(url, formatId = 'MP4') {
                if (spanElement) spanElement.textContent = 'Sending...';
                btn.disabled = true;
                btn.style.backgroundColor = '#999999';
                btn.style.cursor = 'wait';

                GM_xmlhttpRequest({
                    method: "POST",
                    url: SERVER_URL,
                    headers: { "Content-Type": "application/json" },
                    data: JSON.stringify({ url: url, format: formatId }),
                    onload: function (response) {
                        try {
                            const result = JSON.parse(response.responseText);
                            if (response.status !== 202 && response.status !== 200) {
                                console.error('Download error:', result);
                                resetBtnError('Error: ' + (result.error || 'Failed to trigger download'));
                            } else {
                                pollStatus(btn, result.job_id);
                            }
                        } catch (e) {
                            console.error("Failed to parse response", e);
                            resetBtnError('Failed to parse response from server.');
                        }
                    },
                    onerror: () => resetBtnError('Error triggering download. Server might be down.')
                });
            }
        });

        return btn;
    }

    // =============== GLOBAL DASHBOARD LOGIC ===============

    let dashboardEl = null;
    let isDragging = false;
    let dragStartX = 0, dragStartY = 0;

    function initDashboard() {
        dashboardEl = document.createElement('div');
        dashboardEl.id = 'yt-dlp-global-dashboard';
        dashboardEl.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; width: 320px;
            background: #181818; border: 1px solid #333; border-radius: 12px;
            color: white; font-family: 'Roboto', sans-serif; z-index: 999999;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8); display: none;
            overflow: hidden; transition: opacity 0.3s;
        `;

        const header = document.createElement('div');
        header.style.cssText = `
            background: #252525; padding: 12px 14px; display: flex;
            justify-content: space-between; align-items: center;
            border-bottom: 1px solid #333; cursor: grab; user-select: none;
        `;
        header.innerHTML = '<span style="font-weight:600; font-size:14px; display:flex; align-items:center; gap:6px;">🚀 Downloads</span>';

        // Dragging logic
        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            dragStartX = e.clientX - dashboardEl.getBoundingClientRect().left;
            dragStartY = e.clientY - dashboardEl.getBoundingClientRect().top;
            header.style.cursor = 'grabbing';
            document.body.style.userSelect = 'none';
        });
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const left = e.clientX - dragStartX;
            const top = e.clientY - dragStartY;
            dashboardEl.style.left = `${left}px`;
            dashboardEl.style.top = `${top}px`;
            dashboardEl.style.right = 'auto'; // Disable bottom/right positioning once dragged
            dashboardEl.style.bottom = 'auto';
        });
        document.addEventListener('mouseup', () => {
            isDragging = false;
            header.style.cursor = 'grab';
            document.body.style.userSelect = '';
        });

        const listContainer = document.createElement('div');
        listContainer.id = 'yt-dlp-dash-list';
        listContainer.style.cssText = 'max-height: 300px; overflow-y: auto; padding: 12px;';

        dashboardEl.appendChild(header);
        dashboardEl.appendChild(listContainer);
        document.body.appendChild(dashboardEl);
    }

    function updateDashboard(statuses) {
        if (!dashboardEl) initDashboard();

        const list = document.getElementById('yt-dlp-dash-list');
        list.innerHTML = '';

        // Check for active downloads
        let activeCount = 0;
        const activeJobs = [];
        for (const [jobId, d] of Object.entries(statuses)) {
            // Include starting, downloading, processing. Do not show ones finished > 10秒 ago
            if (['starting', 'downloading', 'processing'].includes(d.status) ||
                (d.status === 'finished' && (!d.finished_at || Date.now() - (d.finished_at * 1000) < 10000)) ||
                (d.status === 'error' && (!d.error_at || Date.now() - (d.error_at * 1000) < 10000))) {
                activeCount++;
                activeJobs.push({ id: jobId, ...d });
            }
        }

        if (activeCount === 0) {
            dashboardEl.style.display = 'none';
            return;
        }

        dashboardEl.style.display = 'block';

        activeJobs.forEach(job => {
            const item = document.createElement('div');
            item.style.cssText = 'margin-bottom: 12px; font-size: 13px;';

            const titleRow = document.createElement('div');
            titleRow.style.cssText = 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; font-weight: 500;';
            titleRow.textContent = job.filename || 'Unknown Title';

            const statusRow = document.createElement('div');
            statusRow.style.cssText = 'display: flex; justify-content: space-between; font-size: 11px; color: #aaa; margin-bottom: 4px;';

            let statusText = `${job.percent} at ${job.speed}`;
            if (job.status === 'starting') statusText = 'Starting...';
            if (job.status === 'processing') statusText = 'Merging Audio & Video...';
            if (job.status === 'finished') statusText = 'Complete!';
            if (job.status === 'error') statusText = 'Error!';

            statusRow.innerHTML = `<span>${statusText}</span> <span>${job.status === 'downloading' ? job.eta || '' : ''}</span>`;

            const barBg = document.createElement('div');
            barBg.style.cssText = 'height: 4px; background: #333; border-radius: 2px; overflow: hidden;';

            const barFill = document.createElement('div');
            let percentVal = parseFloat(job.percent || 0);
            if (job.status === 'processing' || job.status === 'finished') percentVal = 100;

            let color = '#2b74e2'; // blue
            if (job.status === 'processing') color = '#f39c12'; // orange
            if (job.status === 'finished') color = '#2ecc71'; // green
            if (job.status === 'error') color = '#e74c3c'; // red

            barFill.style.cssText = `height: 100%; width: ${percentVal}%; background: ${color}; transition: width 0.3s;`;
            barBg.appendChild(barFill);

            item.appendChild(titleRow);
            item.appendChild(statusRow);
            item.appendChild(barBg);
            list.appendChild(item);
        });
    }

    // Global poller
    setInterval(() => {
        GM_xmlhttpRequest({
            method: "GET",
            url: PROGRESS_URL,
            onload: function (response) {
                try {
                    const statuses = JSON.parse(response.responseText);
                    updateDashboard(statuses);
                } catch (e) { }
            }
        });
    }, 1000);

    let lastUrl = '';
    let prefetchCache = { url: null, status: 'idle', data: null, error: null };

    function prefetchFormats(url) {
        if (prefetchCache.status === 'fetching' && prefetchCache.url === url) return;
        prefetchCache = { url: url, status: 'fetching', data: null, error: null };

        GM_xmlhttpRequest({
            method: "POST",
            url: 'http://127.0.0.1:5000/get_formats',
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify({ url: url }),
            onload: function (res) {
                try {
                    const result = JSON.parse(res.responseText);
                    if (result.status === 'success') {
                        prefetchCache.status = 'done';
                        prefetchCache.data = result;
                    } else {
                        prefetchCache.status = 'error';
                        prefetchCache.error = result.error || 'Unknown server error';
                    }
                } catch (e) {
                    prefetchCache.status = 'error';
                    prefetchCache.error = 'Failed to parse format JSON.';
                }
            },
            onerror: () => {
                prefetchCache.status = 'error';
                prefetchCache.error = 'Server is offline.';
            }
        });
    }

    // Try to safely inject the button repeatedly (YouTube is SPA)
    setInterval(() => {
        if (!window.location.href.includes('/watch')) return;

        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            prefetchFormats(lastUrl);
        }

        injectButton();
    }, 1000);

    function injectButton() {
        if (!window.location.href.includes('watch?v=')) return false;
        if (document.getElementById('yt-downloader-btn')) return true; // Already injected

        // YouTube changes these IDs constantly. We check all of them.
        const possibleTargets = [
            { selector: '#owner-inner', position: 'append' },
            { selector: '#top-row.ytd-watch-metadata', position: 'append' },
            { selector: '#owner.ytd-watch-metadata', position: 'append' },
            { selector: '#actions.ytd-watch-metadata', position: 'append' },
            { selector: 'ytd-watch-metadata', position: 'prepend' }, // Fallback
            { selector: '#top-level-buttons-computed', position: 'prepend' },
            { selector: '#actions-inner', position: 'prepend' }
        ];

        let targetContainer = null;
        let injectionMethod = 'append';

        for (const target of possibleTargets) {
            const el = document.querySelector(target.selector);
            if (el) {
                targetContainer = el;
                injectionMethod = target.position;
                console.log("[YT-Downloader] Found injection target:", target.selector);
                break;
            }
        }

        if (targetContainer) {
            const button = createDownloadButton();

            // Try to put it right after the subscribe button if we are in the owner area
            const subscribeBtn = targetContainer.querySelector('ytd-subscribe-button-renderer, #subscribe-button');

            if (subscribeBtn) {
                console.log("[YT-Downloader] Injecting beside Subscribe button");
                subscribeBtn.parentElement.insertBefore(button, subscribeBtn.nextSibling);
            } else if (injectionMethod === 'prepend') {
                console.log("[YT-Downloader] Prepending to target container");
                targetContainer.insertBefore(button, targetContainer.firstChild);
            } else {
                console.log("[YT-Downloader] Appending to target container");
                targetContainer.appendChild(button);
            }
            return true; // Successfully injected
        }

        console.log("[YT-Downloader] Could not find any target containers yet. Retrying...");
        return false; // Did not find a place to inject yet
    }

    // YouTube is a Single Page Application (SPA). The DOM is built asynchronously.
    // Instead of relying purely on extremely noisy MutationObservers, we aggressively
    // poll for the target elements until they exist, then back off.
    let injectionAttempts = 0;
    const injectionInterval = setInterval(() => {
        if (injectButton()) {
            // Success! We can slow down the polling significantly.
            // We don't clear it entirely because the user might click a related video
            // Which destroys and rebuilds the DOM without reloading the page.
            injectionAttempts = 0;
        } else {
            injectionAttempts++;
            if (injectionAttempts > 120) { // After 60 seconds of trying, give up.
                console.log("[YT-Downloader] Gave up trying to inject button after 120 attempts.");
                clearInterval(injectionInterval);
            }
        }
    }, 500);

    // Also listen to YouTube's custom SPA navigation event to instantly trigger a retry
    window.addEventListener('yt-navigate-finish', () => {
        console.log("[YT-Downloader] Navigation detected, resetting injection logic.");
        injectionAttempts = 0;
        injectButton();
    });

})();
