// ==UserScript==
// @name         One-Click YouTube Downloader
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Adds a download button to YouTube videos that communicates with a local Flask server to trigger downloads.
// @author       Aazan Noor Khuwaja
// @match        *://*.youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function () {
    'use strict';

    const SERVER_URL = 'http://127.0.0.1:5000/download';
    const STATUS_URL = 'http://127.0.0.1:5000/status';
    const CONFIG_URL = 'http://127.0.0.1:5000/config';
    const BROWSE_URL = 'http://127.0.0.1:5000/browse';

    // =============== SETTINGS PANEL ===============

    function createSettingsPanel() {
        // Backdrop (click outside to close)
        const backdrop = document.createElement('div');
        backdrop.id = 'yt-dl-settings-backdrop';
        backdrop.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 99998;
            display: none; backdrop-filter: blur(3px);
        `;

        const panel = document.createElement('div');
        panel.id = 'yt-dl-settings-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: #1e1e1e; color: #fff; border-radius: 16px;
            padding: 28px 32px; z-index: 99999; width: 460px;
            font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5); display: none;
            border: 1px solid rgba(255,255,255,0.1);
        `;

        // Note: Do NOT use innerHTML on YouTube — TrustedTypes policy blocks it silently

        // === Title Row ===
        const titleRow = document.createElement('div');
        titleRow.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;';

        const title = document.createElement('h3');
        title.textContent = '⚙️ Downloader Settings';
        title.style.cssText = 'margin:0; font-size:18px; font-weight:600; color:#fff;';

        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            background: none; border: none; color: #888; font-size: 20px;
            cursor: pointer; padding: 4px 8px; border-radius: 6px;
        `;
        closeBtn.addEventListener('mouseenter', () => closeBtn.style.color = '#fff');
        closeBtn.addEventListener('mouseleave', () => closeBtn.style.color = '#888');
        closeBtn.addEventListener('click', () => hideSettings());

        titleRow.appendChild(title);
        titleRow.appendChild(closeBtn);
        panel.appendChild(titleRow);

        // === Download Folder ===
        const folderLabel = document.createElement('label');
        folderLabel.textContent = '📁 Download Folder';
        folderLabel.style.cssText = 'display:block; margin-bottom:8px; font-size:13px; color:#aaa; font-weight:500;';
        panel.appendChild(folderLabel);

        // Current folder display + Browse button row
        const folderRow = document.createElement('div');
        folderRow.style.cssText = 'display:flex; gap:8px; margin-bottom:8px; align-items:center;';

        const folderDisplay = document.createElement('div');
        folderDisplay.id = 'yt-dl-folder-display';
        folderDisplay.style.cssText = `
            flex: 1; padding: 10px 14px; background: #2a2a2a;
            border: 1px solid #444; border-radius: 10px;
            color: #fff; font-size: 13px; overflow: hidden;
            text-overflow: ellipsis; white-space: nowrap;
        `;
        folderDisplay.textContent = '~/Downloads';

        const browseBtn = document.createElement('button');
        browseBtn.textContent = '📂 Browse';
        browseBtn.style.cssText = `
            padding: 10px 16px; background: #333; color: #fff;
            border: 1px solid #555; border-radius: 10px; font-size: 13px;
            cursor: pointer; white-space: nowrap; transition: all 0.2s;
        `;
        browseBtn.addEventListener('mouseenter', () => browseBtn.style.background = '#444');
        browseBtn.addEventListener('mouseleave', () => browseBtn.style.background = '#333');
        browseBtn.addEventListener('click', () => openFolderBrowser());

        folderRow.appendChild(folderDisplay);
        folderRow.appendChild(browseBtn);
        panel.appendChild(folderRow);

        // Hidden input to store the actual path
        const folderInput = document.createElement('input');
        folderInput.id = 'yt-dl-folder-input';
        folderInput.type = 'hidden';
        folderInput.value = '~/Downloads';
        panel.appendChild(folderInput);

        // === Folder Browser Container (initially hidden) ===
        const browserContainer = document.createElement('div');
        browserContainer.id = 'yt-dl-folder-browser';
        browserContainer.style.cssText = `
            display: none; background: #252525; border: 1px solid #444;
            border-radius: 10px; margin-bottom: 16px; overflow: hidden;
        `;

        // Browser header with current path + parent button
        const browserHeader = document.createElement('div');
        browserHeader.id = 'yt-dl-browser-header';
        browserHeader.style.cssText = `
            display: flex; align-items: center; gap: 8px;
            padding: 10px 12px; background: #1a1a1a;
            border-bottom: 1px solid #333; font-size: 12px; color: #888;
        `;

        const parentBtn = document.createElement('button');
        parentBtn.id = 'yt-dl-parent-btn';
        parentBtn.textContent = '⬆️';
        parentBtn.title = 'Go to parent folder';
        parentBtn.style.cssText = `
            background: none; border: 1px solid #555; border-radius: 6px;
            color: #fff; font-size: 14px; cursor: pointer; padding: 2px 8px;
            transition: all 0.2s;
        `;
        parentBtn.addEventListener('mouseenter', () => parentBtn.style.borderColor = '#cc0000');
        parentBtn.addEventListener('mouseleave', () => parentBtn.style.borderColor = '#555');

        const pathDisplay = document.createElement('span');
        pathDisplay.id = 'yt-dl-browser-path';
        pathDisplay.style.cssText = 'flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#aaa;';

        browserHeader.appendChild(parentBtn);
        browserHeader.appendChild(pathDisplay);
        browserContainer.appendChild(browserHeader);

        // Folder list
        const folderList = document.createElement('div');
        folderList.id = 'yt-dl-folder-list';
        folderList.style.cssText = 'max-height: 200px; overflow-y: auto; padding: 4px 0;';
        browserContainer.appendChild(folderList);

        // Select button at bottom of browser
        const selectRow = document.createElement('div');
        selectRow.style.cssText = 'padding: 8px 12px; border-top: 1px solid #333; display:flex; justify-content:flex-end;';

        const selectBtn = document.createElement('button');
        selectBtn.textContent = '✅ Select This Folder';
        selectBtn.style.cssText = `
            padding: 8px 16px; background: #2ecc71; color: #fff;
            border: none; border-radius: 8px; font-size: 13px; font-weight: 600;
            cursor: pointer; transition: all 0.2s;
        `;
        selectBtn.addEventListener('mouseenter', () => selectBtn.style.background = '#27ae60');
        selectBtn.addEventListener('mouseleave', () => selectBtn.style.background = '#2ecc71');
        selectBtn.addEventListener('click', () => {
            const pathEl = document.getElementById('yt-dl-browser-path');
            const currentPath = pathEl ? pathEl.textContent : '';
            if (currentPath) {
                document.getElementById('yt-dl-folder-input').value = currentPath;
                document.getElementById('yt-dl-folder-display').textContent = currentPath;
                document.getElementById('yt-dl-folder-browser').style.display = 'none';
            }
        });

        selectRow.appendChild(selectBtn);
        browserContainer.appendChild(selectRow);
        panel.appendChild(browserContainer);

        // === Browser for Cookies ===
        const browserLabel = document.createElement('label');
        browserLabel.textContent = '🌐 Browser (for login cookies)';
        browserLabel.style.cssText = 'display:block; margin-bottom:8px; margin-top:8px; font-size:13px; color:#aaa; font-weight:500;';
        panel.appendChild(browserLabel);

        const browserSelect = document.createElement('select');
        browserSelect.id = 'yt-dl-browser-select';
        browserSelect.style.cssText = `
            width: 100%; padding: 10px 14px; box-sizing: border-box;
            background: #2a2a2a; border: 1px solid #444; border-radius: 10px;
            color: #fff; font-size: 14px; margin-bottom: 6px;
            outline: none; cursor: pointer; appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23888' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat; background-position: right 14px center;
        `;

        const options = [
            { value: 'auto', label: '🔍 Auto-Detect (Recommended)' },
            { value: 'brave', label: 'Brave' },
            { value: 'chrome', label: 'Google Chrome' },
            { value: 'chromium', label: 'Chromium' },
            { value: 'firefox', label: 'Mozilla Firefox' },
            { value: 'edge', label: 'Microsoft Edge' },
            { value: 'opera', label: 'Opera' },
            { value: 'none', label: '🚫 None (no cookies)' },
        ];

        options.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.value;
            el.textContent = opt.label;
            el.style.cssText = 'background: #2a2a2a; color: #fff;';
            browserSelect.appendChild(el);
        });
        panel.appendChild(browserSelect);

        const browserHint = document.createElement('p');
        browserHint.textContent = 'Which browser to borrow cookies from. "Auto-Detect" finds your browser automatically.';
        browserHint.style.cssText = 'font-size:11px; color:#666; margin:0 0 24px 0;';
        panel.appendChild(browserHint);

        // === Status Message ===
        const statusMsg = document.createElement('div');
        statusMsg.id = 'yt-dl-settings-status';
        statusMsg.style.cssText = `
            text-align: center; font-size: 13px; color: #2ecc71;
            min-height: 20px; margin-bottom: 16px; display: none;
        `;
        panel.appendChild(statusMsg);

        // === Save Button ===
        const saveBtn = document.createElement('button');
        saveBtn.textContent = '💾 Save Settings';
        saveBtn.style.cssText = `
            width: 100%; padding: 12px; background: #cc0000; color: #fff;
            border: none; border-radius: 10px; font-size: 15px; font-weight: 600;
            cursor: pointer; transition: all 0.2s;
        `;
        saveBtn.addEventListener('mouseenter', () => saveBtn.style.background = '#ff0000');
        saveBtn.addEventListener('mouseleave', () => saveBtn.style.background = '#cc0000');
        saveBtn.addEventListener('click', () => saveSettings(statusMsg));
        panel.appendChild(saveBtn);

        backdrop.addEventListener('click', () => hideSettings());

        document.body.appendChild(backdrop);
        document.body.appendChild(panel);
    }

    function openFolderBrowser(startPath) {
        const container = document.getElementById('yt-dl-folder-browser');
        if (container) container.style.display = 'block';

        const path = startPath || document.getElementById('yt-dl-folder-input').value || '~';
        loadFolderList(path);
    }

    function loadFolderList(path) {
        const folderList = document.getElementById('yt-dl-folder-list');
        const pathDisplay = document.getElementById('yt-dl-browser-path');
        const parentBtn = document.getElementById('yt-dl-parent-btn');

        if (!folderList) return;

        // Clear existing items
        while (folderList.firstChild) folderList.removeChild(folderList.firstChild);

        // Show loading
        const loadingEl = document.createElement('div');
        loadingEl.style.cssText = 'padding: 16px; text-align: center; color: #888; font-size: 13px;';
        loadingEl.textContent = 'Loading folders...';
        folderList.appendChild(loadingEl);

        GM_xmlhttpRequest({
            method: "GET",
            url: BROWSE_URL + '?path=' + encodeURIComponent(path),
            onload: function (response) {
                try {
                    const data = JSON.parse(response.responseText);

                    if (data.error) {
                        loadingEl.textContent = '❌ ' + data.error;
                        return;
                    }

                    // Update path display
                    if (pathDisplay) pathDisplay.textContent = data.current;

                    // Setup parent button
                    if (parentBtn) {
                        if (data.parent) {
                            parentBtn.style.opacity = '1';
                            parentBtn.style.cursor = 'pointer';
                            parentBtn.onclick = () => loadFolderList(data.parent);
                        } else {
                            parentBtn.style.opacity = '0.3';
                            parentBtn.style.cursor = 'default';
                            parentBtn.onclick = null;
                        }
                    }

                    // Clear and populate folder list
                    while (folderList.firstChild) folderList.removeChild(folderList.firstChild);

                    if (data.folders.length === 0) {
                        const emptyEl = document.createElement('div');
                        emptyEl.style.cssText = 'padding: 16px; text-align: center; color: #666; font-size: 13px;';
                        emptyEl.textContent = 'No subfolders here';
                        folderList.appendChild(emptyEl);
                        return;
                    }

                    data.folders.forEach(folderName => {
                        const item = document.createElement('div');
                        item.style.cssText = `
                            padding: 8px 14px; cursor: pointer; display: flex;
                            align-items: center; gap: 8px; font-size: 13px;
                            color: #ddd; transition: background 0.15s;
                        `;
                        item.addEventListener('mouseenter', () => item.style.background = '#333');
                        item.addEventListener('mouseleave', () => item.style.background = 'transparent');

                        const icon = document.createElement('span');
                        icon.textContent = '📁';
                        icon.style.fontSize = '14px';

                        const name = document.createElement('span');
                        name.textContent = folderName;

                        item.appendChild(icon);
                        item.appendChild(name);

                        item.addEventListener('click', () => {
                            loadFolderList(data.current + '/' + folderName);
                        });

                        folderList.appendChild(item);
                    });

                } catch (e) {
                    console.error('[YT-Downloader] Failed to load folders:', e);
                    loadingEl.textContent = '❌ Failed to load folders';
                }
            },
            onerror: function () {
                loadingEl.textContent = '❌ Server not running';
            }
        });
    }

    function showSettings() {
        let panel = document.getElementById('yt-dl-settings-panel');
        let backdrop = document.getElementById('yt-dl-settings-backdrop');
        if (!panel) {
            createSettingsPanel();
            panel = document.getElementById('yt-dl-settings-panel');
            backdrop = document.getElementById('yt-dl-settings-backdrop');
        }

        // Hide folder browser when reopening
        const browser = document.getElementById('yt-dl-folder-browser');
        if (browser) browser.style.display = 'none';

        // Load current settings from server
        GM_xmlhttpRequest({
            method: "GET",
            url: CONFIG_URL,
            onload: function (response) {
                try {
                    const config = JSON.parse(response.responseText);
                    const dir = config.download_dir || '~/Downloads';
                    document.getElementById('yt-dl-folder-input').value = dir;
                    document.getElementById('yt-dl-folder-display').textContent = dir;
                    document.getElementById('yt-dl-browser-select').value = config.browser || 'auto';
                } catch (e) {
                    console.error('[YT-Downloader] Failed to load settings:', e);
                }
            },
            onerror: function () {
                document.getElementById('yt-dl-folder-input').value = '~/Downloads';
                document.getElementById('yt-dl-folder-display').textContent = '~/Downloads';
                document.getElementById('yt-dl-browser-select').value = 'auto';
            }
        });

        panel.style.display = 'block';
        backdrop.style.display = 'block';
    }

    function hideSettings() {
        const panel = document.getElementById('yt-dl-settings-panel');
        const backdrop = document.getElementById('yt-dl-settings-backdrop');
        if (panel) panel.style.display = 'none';
        if (backdrop) backdrop.style.display = 'none';
    }

    function saveSettings(statusMsg) {
        const folderInput = document.getElementById('yt-dl-folder-input');
        const browserSelect = document.getElementById('yt-dl-browser-select');

        const newConfig = {
            download_dir: folderInput.value.trim(),
            browser: browserSelect.value
        };

        statusMsg.style.display = 'block';
        statusMsg.textContent = 'Saving...';
        statusMsg.style.color = '#f39c12';

        GM_xmlhttpRequest({
            method: "POST",
            url: CONFIG_URL,
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify(newConfig),
            onload: function (response) {
                try {
                    const result = JSON.parse(response.responseText);
                    if (response.status === 200) {
                        statusMsg.textContent = '✅ Settings saved!';
                        statusMsg.style.color = '#2ecc71';
                        setTimeout(() => {
                            statusMsg.style.display = 'none';
                        }, 2000);
                    } else {
                        statusMsg.textContent = '❌ ' + (result.error || 'Failed to save');
                        statusMsg.style.color = '#e74c3c';
                    }
                } catch (e) {
                    statusMsg.textContent = '❌ Unexpected error';
                    statusMsg.style.color = '#e74c3c';
                }
            },
            onerror: function () {
                statusMsg.textContent = '❌ Server not running! Start the server first.';
                statusMsg.style.color = '#e74c3c';
            }
        });
    }

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

            if (spanElement) spanElement.textContent = 'Sending...';
            btn.disabled = true;
            btn.style.backgroundColor = '#999999';
            btn.style.cursor = 'wait';

            GM_xmlhttpRequest({
                method: "POST",
                url: SERVER_URL,
                headers: {
                    "Content-Type": "application/json"
                },
                data: JSON.stringify({ url: videoUrl }),
                onload: function (response) {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (response.status !== 202 && response.status !== 200) {
                            console.error('Download error:', result);
                            alert('Error: ' + (result.error || 'Failed to trigger download'));

                            if (spanElement) spanElement.textContent = 'Download';
                            btn.disabled = false;
                            btn.style.backgroundColor = '#cc0000';
                            btn.style.cursor = 'pointer';
                        } else {
                            // Download accepted, start polling for status updates
                            pollStatus(btn, result.job_id);
                        }
                    } catch (e) {
                        console.error("Failed to parse response", e);
                        // Reset button so it doesn't get stuck
                        if (spanElement) spanElement.textContent = 'Download';
                        btn.disabled = false;
                        btn.style.backgroundColor = '#cc0000';
                        btn.style.cursor = 'pointer';
                    }
                },
                onerror: function (error) {
                    if (spanElement) spanElement.textContent = 'Download';
                    btn.disabled = false;
                    btn.style.backgroundColor = '#cc0000';
                    btn.style.cursor = 'pointer';

                    console.error('GM_xmlhttpRequest error:', error);
                    alert('Error connecting to local server. Make sure the Python Flask app is running at ' + SERVER_URL);
                }
            });
        });

        return btn;
    }

    function createSettingsGearButton() {
        const gear = document.createElement('button');
        gear.id = 'yt-downloader-gear';
        gear.textContent = '⚙️';
        gear.title = 'Downloader Settings';
        gear.style.cssText = `
            background: none; border: none; font-size: 20px;
            cursor: pointer; margin-left: 4px; padding: 4px 6px;
            border-radius: 50%; transition: all 0.2s; opacity: 0.6;
            line-height: 1; display: flex; align-items: center;
        `;
        gear.addEventListener('mouseenter', () => {
            gear.style.opacity = '1';
            gear.style.transform = 'rotate(45deg)';
        });
        gear.addEventListener('mouseleave', () => {
            gear.style.opacity = '0.6';
            gear.style.transform = 'rotate(0deg)';
        });
        gear.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            e.stopImmediatePropagation();
            console.log('[YT-Downloader] Gear icon clicked');
            // Use setTimeout to break out of YouTube's event handling chain
            setTimeout(() => {
                try {
                    showSettings();
                } catch (err) {
                    console.error('[YT-Downloader] Settings panel error:', err);
                    alert('Settings panel error: ' + err.message);
                }
            }, 0);
        });
        return gear;
    }

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
            const gearBtn = createSettingsGearButton();

            // Wrap both in a flex container for clean alignment
            const wrapper = document.createElement('div');
            wrapper.id = 'yt-downloader-wrapper';
            wrapper.style.cssText = 'display: flex; align-items: center;';
            wrapper.appendChild(button);
            wrapper.appendChild(gearBtn);

            // Try to put it right after the subscribe button if we are in the owner area
            const subscribeBtn = targetContainer.querySelector('ytd-subscribe-button-renderer, #subscribe-button');

            if (subscribeBtn) {
                console.log("[YT-Downloader] Injecting beside Subscribe button");
                subscribeBtn.parentElement.insertBefore(wrapper, subscribeBtn.nextSibling);
            } else if (injectionMethod === 'prepend') {
                console.log("[YT-Downloader] Prepending to target container");
                targetContainer.insertBefore(wrapper, targetContainer.firstChild);
            } else {
                console.log("[YT-Downloader] Appending to target container");
                targetContainer.appendChild(wrapper);
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
