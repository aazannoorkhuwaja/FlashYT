document.addEventListener('DOMContentLoaded', () => {
    // === THEME HANDLING ===
    const body = document.body;
    const themeToggle = document.getElementById('theme-toggle');
    const iconSun = document.getElementById('icon-sun');
    const iconMoon = document.getElementById('icon-moon');
    let isDark = true;
    let hostStatusInfo = null;
    let releaseInfo = null;
    let updateOpenUrl = "https://github.com/aazannoorkhuwaja/FlashYT/releases/latest";
    let updateCopyCommand = null;

    function toggleTheme() {
        isDark = !isDark;
        if (isDark) {
            body.classList.replace('theme-light', 'theme-dark');
            iconSun.classList.remove('hidden');
            iconMoon.classList.add('hidden');
        } else {
            body.classList.replace('theme-dark', 'theme-light');
            iconSun.classList.add('hidden');
            iconMoon.classList.remove('hidden');
        }
        chrome.storage.local.set({ theme: isDark ? 'dark' : 'light' });
    }

    themeToggle.addEventListener('click', toggleTheme);
    chrome.storage.local.get(['theme'], (result) => {
        if (result.theme === 'light') {
            toggleTheme(); // Starts dark by default
        }
    });

    // === TAB HANDLING ===
    const tabBtns = document.querySelectorAll('.tab-btn');
    const views = document.querySelectorAll('.view');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');

            // Update active states for buttons
            tabBtns.forEach(b => {
                b.classList.remove('active');
                b.querySelector('.tab-indicator')?.classList.add('hidden');
            });
            btn.classList.add('active');
            btn.querySelector('.tab-indicator')?.classList.remove('hidden');

            // Update visible view
            views.forEach(v => {
                if (v.id === `view-${target}`) {
                    v.classList.remove('hidden');
                    v.classList.add('active');
                } else {
                    v.classList.add('hidden');
                    v.classList.remove('active');
                }
            });
        });
    });

    // === HEADER BUTTONS ===
    const settingsBtn = document.getElementById('settings-btn');
    settingsBtn.addEventListener('click', () => {
        // Deselect all tabs
        tabBtns.forEach(b => {
            b.classList.remove('active');
            b.querySelector('.tab-indicator')?.classList.add('hidden');
        });

        // Hide all views, show settings
        views.forEach(v => {
            if (v.id === 'view-settings') {
                v.classList.remove('hidden');
                v.classList.add('active');
            } else {
                v.classList.add('hidden');
                v.classList.remove('active');
            }
        });
    });

    // === SETTINGS LOAD & SAVE ===
    const maxConcurrentInput = document.getElementById('setting-max-concurrent');
    const saveLocationInput = document.getElementById('setting-save-location');
    const saveSettingsBtn = document.getElementById('save-settings-btn');

    chrome.storage.local.get({
        max_concurrent: 3,
        save_location: '~/Downloads'
    }, (res) => {
        if (maxConcurrentInput) maxConcurrentInput.value = res.max_concurrent;
        if (saveLocationInput) saveLocationInput.value = res.save_location;
    });

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            const maxVal = parseInt(maxConcurrentInput.value, 10) || 3;
            const locVal = saveLocationInput.value || '~/Downloads';
            chrome.storage.local.set({
                max_concurrent: maxVal,
                save_location: locVal
            }, () => {
                const oldText = saveSettingsBtn.textContent;
                saveSettingsBtn.textContent = 'Saved!';
                saveSettingsBtn.style.backgroundColor = '#2ecc71';
                setTimeout(() => {
                    saveSettingsBtn.textContent = oldText;
                    saveSettingsBtn.style.backgroundColor = '';
                }, 2000);
            });
        });
    }

    const browseBtn = document.getElementById('browse-folder-btn');
    if (browseBtn) {
        browseBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: "OPEN_FOLDER", path: "" });
        });
    }

    const emailBtn = document.getElementById('contact-email-btn');
    if (emailBtn) {
        emailBtn.addEventListener('click', async () => {
            const email = emailBtn.getAttribute('data-email') || '';
            if (!email) return;
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(email);
                } else {
                    const temp = document.createElement('input');
                    temp.value = email;
                    document.body.appendChild(temp);
                    temp.select();
                    document.execCommand('copy');
                    temp.remove();
                }
                const label = document.getElementById('contact-email-value');
                if (label) {
                    const original = label.textContent;
                    label.textContent = 'Copied to clipboard';
                    setTimeout(() => { label.textContent = original; }, 1400);
                }
            } catch (_err) {
                const label = document.getElementById('contact-email-value');
                if (label) label.textContent = email;
            }
        });
    }

    // === UTILITIES ===
    function formatSize(bytes) {
        if (!bytes) return 'Calculating...';
        if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`;
        if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
        return `${(bytes / 1024).toFixed(0)} KB`;
    }

    function formatSpeed(bytesPerSec) {
        if (!bytesPerSec) return '–';
        return `${(bytesPerSec / 1048576).toFixed(1)} MB/s`;
    }

    async function copyText(text) {
        if (!text) return false;
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                return true;
            }
            const temp = document.createElement('input');
            temp.value = text;
            document.body.appendChild(temp);
            temp.select();
            document.execCommand('copy');
            temp.remove();
            return true;
        } catch (_) {
            return false;
        }
    }

    function calcEta(total, done, speed) {
        if (!speed || done >= total) return "–";
        const s = Math.round((total - done) / speed);
        return s > 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
    }

    function createProgressRing(pct) {
        const size = 36;
        const stroke = 3;
        const r = (size - stroke * 2) / 2;
        const circ = 2 * Math.PI * r;
        const off = circ - (pct / 100) * circ;

        return `
        <svg width="${size}" height="${size}" class="progress-ring" style="transform: rotate(-90deg);">
            <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--border)" stroke-width="${stroke}"></circle>
            <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" class="progress-ring-circle" stroke="#ff0000" stroke-width="${stroke}" stroke-dasharray="${circ}" stroke-dashoffset="${off}" stroke-linecap="round"></circle>
        </svg>
        `;
    }

    const icons = {
        video: `<svg class="w-7 h-7 text-muted" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="m10 13 4 4 4-4"></path></svg>`,
        play: `<svg class="w-3-5 h-3-5 text-emerald" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`,
        pause: `<svg class="w-3-5 h-3-5 text-amber" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`,
        trash: `<svg class="w-3-5 h-3-5 text-red opacity-70 hover-opacity-100 transition-opacity" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
        check: `<svg class="w-3-5 h-3-5 text-emerald" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
        error: `<svg class="w-3-5 h-3-5 text-red" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
        loader: `<svg class="w-3 h-3 text-muted animate-spin" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`,
        folder: `<svg class="w-3-5 h-3-5 text-muted opacity-70 hover-opacity-100 transition-opacity" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`
    };

    function generateDownloadHtml(item) {
        const isActive = ['downloading', 'starting', 'pausing', 'resuming', 'cancelling'].includes(item.status);
        const canPause = ['downloading', 'starting', 'resuming'].includes(item.status);
        const canResume = item.status === 'paused';
        const isTerminal = ['completed', 'error', 'cancelled'].includes(item.status);

        return `
        <div class="dl-item group ${isActive ? 'active' : ''}">
            ${isActive ? '<div class="dl-active-glow"></div>' : ''}
            <div class="relative flex gap-3 p-3">
                <div class="dl-thumb-wrap">
                    ${item.thumbnail ? `<img src="${item.thumbnail}" class="dl-thumb-img" />` : `<div class="w-full h-full flex items-center justify-center">${icons.video}</div>`}
                    <div class="dl-thumb-gradient"></div>
                    <span class="dl-format-badge">${item.format || 'MP4'}</span>
                </div>
                
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold leading-tight mb-1-5 line-clamp-2 text-brand m-0">${item.title}</p>
                    <div class="flex items-center gap-2 mb-2">
                        <span class="dl-quality-badge">${item.quality || 'Auto'}</span>
                        <span class="text-xs text-muted">${formatSize(item.totalSize)}</span>
                        ${item.status === 'downloading' ? `<span class="text-xs font-medium text-yellow">${formatSpeed(item.speed)}</span>` : ''}
                    </div>

                    ${isActive || item.status === 'paused' ? `
                        <div>
                            <div class="dl-progress-track">
                                <div class="dl-progress-bar" style="width: ${item.progress}%"></div>
                            </div>
                            <div class="flex justify-between text-xs-sub text-muted font-mono">
                                <span>${item.progress}% • ${formatSize(item.downloaded)} / ${formatSize(item.totalSize)}</span>
                                <span>ETA ${calcEta(item.totalSize, item.downloaded, item.speed)}</span>
                            </div>
                        </div>
                    ` : ''}

                    ${item.status === 'completed' ? `
                        <div class="flex items-center gap-1-5 text-emerald text-xs font-medium mt-1">
                            ${icons.check} Completed
                        </div>
                    ` : ''}

                    ${item.status === 'paused' ? `
                        <div class="flex items-center gap-1-5 text-amber text-xs font-medium mt-1">
                            Paused at ${item.progress}%
                        </div>
                    ` : ''}

                    ${item.status === 'pausing' ? `
                        <div class="flex items-center gap-1-5 text-amber text-xs font-medium mt-1">
                            ${icons.loader} Pausing...
                        </div>
                    ` : ''}

                    ${item.status === 'resuming' ? `
                        <div class="flex items-center gap-1-5 text-yellow text-xs font-medium mt-1">
                            ${icons.loader} Resuming...
                        </div>
                    ` : ''}

                    ${item.status === 'cancelling' ? `
                        <div class="flex items-center gap-1-5 text-red text-xs font-medium mt-1">
                            ${icons.loader} Cancelling...
                        </div>
                    ` : ''}

                    ${item.status === 'error' ? `
                        <div class="flex items-center gap-1-5 text-red text-xs font-medium mt-1">
                            ${icons.error} Failed (${item.progress}%)
                        </div>
                    ` : ''}

                    ${item.status === 'cancelled' ? `
                        <div class="flex items-center gap-1-5 text-red text-xs font-medium mt-1">
                            ${icons.error} Cancelled
                        </div>
                    ` : ''}

                    ${item.status === 'queued' ? `
                        <div class="flex items-center gap-1-5 text-xs text-muted mt-1">
                            ${icons.loader} In Queue
                        </div>
                    ` : ''}
                </div>
                
                <div class="flex flex-col items-center gap-1-5 pt-1">
                    ${isActive ? createProgressRing(item.progress) : ''}
                    
                    ${(canPause || canResume) ? `
                        <button class="dl-action-btn hover-opacity-90" data-action="${canPause ? 'pause' : 'resume'}" data-id="${item.id}" title="${canPause ? 'Pause' : 'Resume'}">
                            ${canPause ? icons.pause : icons.play}
                        </button>
                    ` : ''}
                    
                    <button class="dl-action-btn" data-action="cancel" data-id="${item.id}" title="${isTerminal ? 'Remove' : 'Cancel'}">
                        ${icons.trash}
                    </button>
                </div>
            </div>
        </div>
        `;
    }

    function generateHistoryHtml(item) {
        const pathSafe = (item.path || '').replace(/\\/g, '\\\\').replace(/"/g, '&quot;');
        // Calculate file size. size_mb is stored in megabytes, we need to show MB directly without converting to raw bytes and back
        const sizeDisp = item.size_mb ? parseFloat(item.size_mb).toFixed(1) + ' MB' : '';

        return `
        <div class="dl-item group history-item" data-path="${pathSafe}">
            <div class="relative flex gap-3 p-3 cursor-pointer">
                <div class="dl-thumb-wrap">
                    ${item.thumbnail ? `<img src="${item.thumbnail}" class="dl-thumb-img" />` : `<div class="w-full h-full flex items-center justify-center">${icons.video}</div>`}
                    <div class="dl-thumb-gradient"></div>
                </div>
                
                <div class="flex-1 min-w-0 flex flex-col justify-center">
                    <p class="text-sm font-semibold leading-tight mb-1-5 line-clamp-2 text-brand m-0">${item.title}</p>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-muted">${sizeDisp}</span>
                        ${item.actual_quality ? `<span class="text-xs text-muted">•</span><span class="quality-badge">${item.actual_quality}</span>` : ''}
                        <span class="text-xs text-muted">•</span>
                        <span class="text-xs text-emerald flex items-center gap-1">${icons.check} Saved</span>
                    </div>
                </div>

                <div class="flex flex-col items-center gap-1-5 pt-1">
                    <button class="dl-action-btn" title="Open Folder">
                        ${icons.folder}
                    </button>
                </div>
            </div>
        </div>
        `;
    }

    // === DATA RENDERING ===
    const els = {
        listDownloads: document.getElementById('list-downloads'), // Now History
        listQueue: document.getElementById('list-queue'), // Now Active Queue
        emptyDownloads: document.getElementById('empty-downloads'),
        emptyQueue: document.getElementById('empty-queue'),

        badgeQueue: document.getElementById('badge-queue'),

        countHistory: document.getElementById('count-history'),
        countActive: document.getElementById('count-active'),
        countCompleted: document.getElementById('count-completed'),
        countQueued: document.getElementById('count-queued'),

        statTotal: document.getElementById('stat-total'),
        statCompleted: document.getElementById('stat-completed'),
        statSpeed: document.getElementById('stat-speed'),
        statQueued: document.getElementById('stat-queued'),

        clearBtn: document.getElementById('clear-btn'),
        headerSpeedBadge: document.getElementById('header-speed-badge'),
        headerSpeedText: document.getElementById('header-speed-text'),

        hostStatusText: document.getElementById('host-status-text'),
        hostStatusDot: document.getElementById('host-status-dot'),
        legacyUpdateBanner: document.getElementById('legacy-update-banner'),
        legacyUpdateBannerTitle: document.getElementById('legacy-update-banner-title'),
        legacyUpdateBannerText: document.getElementById('legacy-update-banner-text'),
        legacyUpdateBannerOpenBtn: document.getElementById('legacy-update-banner-open-btn'),
        legacyUpdateBannerCopyBtn: document.getElementById('legacy-update-banner-copy-btn')
    };

    function renderUpdateBanner() {
        if (!els.legacyUpdateBanner) return;

        const hostNeedsUpdate = !!(hostStatusInfo && hostStatusInfo.update_required);
        const appUpdateAvailable = !!(releaseInfo && releaseInfo.updateAvailable);
        if (!hostNeedsUpdate && !appUpdateAvailable) {
            els.legacyUpdateBanner.classList.add('hidden');
            return;
        }

        els.legacyUpdateBanner.classList.remove('hidden');
        if (hostNeedsUpdate) {
            const installed = hostStatusInfo.host_version || "unknown";
            const required = hostStatusInfo.min_required_host_version || "latest";
            updateOpenUrl = hostStatusInfo.updateUrl || updateOpenUrl;
            updateCopyCommand = hostStatusInfo.updateCommand || null;

            els.legacyUpdateBanner.style.background = 'rgba(239,68,68,0.08)';
            els.legacyUpdateBanner.style.borderColor = 'rgba(239,68,68,0.35)';
            els.legacyUpdateBannerTitle.textContent = 'Host Update Required';
            els.legacyUpdateBannerText.textContent = `Installed host ${installed} is outdated. Required ${required}+ for reliable downloads.`;
            els.legacyUpdateBannerOpenBtn.textContent = hostStatusInfo.updateLabel || 'Update Host';
        } else {
            updateOpenUrl = (releaseInfo && releaseInfo.releaseUrl) || updateOpenUrl;
            updateCopyCommand = null;
            els.legacyUpdateBanner.style.background = 'rgba(255,0,0,0.08)';
            els.legacyUpdateBanner.style.borderColor = 'rgba(255,0,0,0.28)';
            els.legacyUpdateBannerTitle.textContent = 'FlashYT Update Available';
            els.legacyUpdateBannerText.textContent = `A newer FlashYT release ${releaseInfo.latestVersion || ''} is available.`;
            els.legacyUpdateBannerOpenBtn.textContent = 'Open Latest Release';
        }

        if (updateCopyCommand) {
            els.legacyUpdateBannerCopyBtn.classList.remove('hidden');
            // On Linux/Mac where we have an updateCommand, we can do one-click update
            if (updateCopyCommand.includes('install.sh')) {
                els.legacyUpdateBannerCopyBtn.textContent = 'Update Now ▶';
                els.legacyUpdateBannerCopyBtn.classList.add('bg-emerald', 'text-white');
                els.legacyUpdateBannerCopyBtn.classList.remove('surface2-bg', 'text-brand');
                els.legacyUpdateBannerCopyBtn._isSelfUpdate = true;
            } else {
                els.legacyUpdateBannerCopyBtn.textContent = 'Copy Update Command';
                els.legacyUpdateBannerCopyBtn.classList.remove('bg-emerald', 'text-white');
                els.legacyUpdateBannerCopyBtn.classList.add('surface2-bg', 'text-brand');
                els.legacyUpdateBannerCopyBtn._isSelfUpdate = false;
            }
        } else {
            els.legacyUpdateBannerCopyBtn.classList.add('hidden');
        }
    }

    function applyUpdateStatus(payload) {
        if (payload?.host) hostStatusInfo = payload.host;
        if (payload?.release) releaseInfo = payload.release;
        renderUpdateBanner();
    }

    // Use event delegation on the persistent container so re-renders don't destroy listeners
    function attachDelegatedListeners(container) {
        if (container._delegated) return; // only attach once
        container._delegated = true;
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('.dl-action-btn[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (action === 'pause') {
                chrome.runtime.sendMessage({ type: 'PAUSE_DOWNLOAD', id }, () => chrome.runtime.lastError);
            } else if (action === 'resume') {
                chrome.runtime.sendMessage({ type: 'RESUME_DOWNLOAD', id }, () => chrome.runtime.lastError);
            } else if (action === 'cancel') {
                chrome.runtime.sendMessage({ type: 'CANCEL_DOWNLOAD', id }, () => chrome.runtime.lastError);
            }
        });
    }

    function renderState(downloads, history = []) {
        let activeHTML = '';
        let historyHTML = '';

        let activeCount = 0;
        let queuedCount = 0;
        let totalSpeed = 0;

        downloads.forEach(d => {
            if (d.status === 'queued') {
                activeHTML += generateDownloadHtml(d);
                queuedCount++;
            } else {
                activeHTML += generateDownloadHtml(d);
                if (['downloading', 'starting', 'pausing', 'resuming', 'cancelling'].includes(d.status)) {
                    activeCount++;
                    totalSpeed += (d.speed || 0);
                }
            }
        });

        history.forEach(h => {
            historyHTML += generateHistoryHtml(h);
        });

        // Downloads Tab (History) Update
        if (historyHTML === '') {
            els.emptyDownloads.classList.remove('hidden');
            els.listDownloads.innerHTML = '';
        } else {
            els.emptyDownloads.classList.add('hidden');
            els.listDownloads.innerHTML = historyHTML;
            // Attach open folder listeners
            els.listDownloads.querySelectorAll('.history-item').forEach(el => {
                el.addEventListener('click', () => {
                    const path = el.getAttribute('data-path');
                    if (path) chrome.runtime.sendMessage({ type: 'OPEN_FOLDER', path });
                });
            });
        }

        // Queue Tab (Active) Update — delegation is attached once, innerHTML can be replaced freely
        attachDelegatedListeners(els.listQueue);
        if (activeHTML === '') {
            els.emptyQueue.classList.remove('hidden');
            els.listQueue.innerHTML = '';
        } else {
            els.emptyQueue.classList.add('hidden');
            els.listQueue.innerHTML = activeHTML;
        }

        // Badges and Text Updates
        if (els.countActive) els.countActive.innerText = activeCount;
        if (els.countHistory) els.countHistory.innerText = history.length;
        if (els.countQueued) els.countQueued.innerText = queuedCount;

        if (els.badgeQueue) {
            els.badgeQueue.innerText = activeCount;
            if (activeCount > 0) els.badgeQueue.classList.remove('hidden');
            else els.badgeQueue.classList.add('hidden');
        }

        // Header Speed Badge
        if (els.headerSpeedBadge) {
            if (totalSpeed > 0) {
                els.headerSpeedBadge.classList.remove('hidden');
                els.headerSpeedText.innerText = formatSpeed(totalSpeed);
            } else {
                els.headerSpeedBadge.classList.add('hidden');
            }
        }

        // Stats Tab updates
        if (els.statTotal) els.statTotal.innerText = history.length + downloads.length;
        if (els.statCompleted) els.statCompleted.innerText = history.length;
        if (els.statSpeed) els.statSpeed.innerText = totalSpeed > 0 ? formatSpeed(totalSpeed) : "–";
        if (els.statQueued) els.statQueued.innerText = queuedCount;

        if (els.clearBtn) {
            if (history.length > 0) els.clearBtn.classList.remove('hidden');
            else els.clearBtn.classList.add('hidden');
        }
    }

    // === COMMUNICATION & POLLING ===
    function fetchDownloads() {
        chrome.runtime.sendMessage({ type: 'GET_DOWNLOADS' }, (response) => {
            chrome.storage.local.get({ history: [] }, (data) => {
                if (response && response.downloads) {
                    renderState(response.downloads, data.history);
                } else {
                    renderState([], data.history);
                }
            });
        });
    }

    function setHostIndicator(status) {
        if (!els.hostStatusText) return;
        if (status === "connected") {
            els.hostStatusText.textContent = "Connected";
            els.hostStatusText.className = "text-emerald";
            if (els.hostStatusDot) els.hostStatusDot.className = "w-2 h-2 rounded-full bg-emerald animate-pulse";
            return;
        }
        if (status === "update_required") {
            els.hostStatusText.textContent = "Update Required";
            els.hostStatusText.className = "text-amber";
            if (els.hostStatusDot) els.hostStatusDot.className = "w-2 h-2 rounded-full bg-amber animate-pulse";
            return;
        }
        if (status === "not_installed") {
            els.hostStatusText.textContent = "Not Installed";
            els.hostStatusText.className = "text-red";
            if (els.hostStatusDot) els.hostStatusDot.className = "w-2 h-2 rounded-full bg-red";
            // Show a banner pointing to the install guide
            if (els.legacyUpdateBanner) {
                els.legacyUpdateBanner.classList.remove('hidden');
                els.legacyUpdateBanner.style.background = 'rgba(239,68,68,0.08)';
                els.legacyUpdateBanner.style.borderColor = 'rgba(239,68,68,0.35)';
                if (els.legacyUpdateBannerTitle) els.legacyUpdateBannerTitle.textContent = 'Native Host Not Installed';
                if (els.legacyUpdateBannerText) els.legacyUpdateBannerText.textContent =
                    'Run the one-line installer, then reload this extension.';
                if (els.legacyUpdateBannerOpenBtn) els.legacyUpdateBannerOpenBtn.textContent = 'Open Install Guide';
                if (els.legacyUpdateBannerCopyBtn) {
                    els.legacyUpdateBannerCopyBtn.textContent = 'Copy Install Command';
                    els.legacyUpdateBannerCopyBtn.classList.remove('hidden');
                    // Store the install command for copy
                    els.legacyUpdateBannerCopyBtn._flashytCmd =
                        'curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh && chmod +x install.sh && ./install.sh';
                }
            }
            return;
        }
        els.hostStatusText.textContent = "Disconnected";
        els.hostStatusText.className = "text-red";
        if (els.hostStatusDot) els.hostStatusDot.className = "w-2 h-2 rounded-full bg-red";
    }

    let _hostCheckInFlight = false;
    function checkHost() {
        if (_hostCheckInFlight) return; // prevent overlapping concurrent calls
        _hostCheckInFlight = true;
        let settled = false;
        const timer = setTimeout(() => {
            if (settled) return;
            settled = true;
            _hostCheckInFlight = false;
            setHostIndicator("disconnected");
            renderUpdateBanner();
        }, 2000);

        chrome.runtime.sendMessage({ type: "CHECK_STATUS" }, (response) => {
            if (settled) return;
            settled = true;
            _hostCheckInFlight = false;
            clearTimeout(timer);
            if (chrome.runtime.lastError || !response) {
                setHostIndicator("disconnected");
                renderUpdateBanner();
                return;
            }
            hostStatusInfo = response || hostStatusInfo;
            setHostIndicator(response.status);
            renderUpdateBanner();
        });
    }

    function fetchUpdateStatus() {
        chrome.runtime.sendMessage({ type: "GET_UPDATE_STATUS" }, (response) => {
            if (!response) return;
            applyUpdateStatus(response);
        });
    }

    if (els.clearBtn) {
        els.clearBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'CLEAR_COMPLETED' });
            chrome.storage.local.set({ history: [] }); // Also clear persistent history
            fetchDownloads();
        });
    }

    chrome.runtime.onMessage.addListener((message) => {
        if (message.type === 'DOWNLOADS_UPDATED') {
            chrome.storage.local.get({ history: [] }, (data) => {
                renderState(message.downloads, data.history);
            });
        }
        if (message.type === 'UPDATE_STATUS' || message.type === 'HOST_STATUS_CHANGED') {
            applyUpdateStatus(message);
            checkHost();
        }
        if (message.type === 'HOST_NOT_INSTALLED') {
            setHostIndicator('not_installed');
        }
        if (message.type === "self_update_progress") {
            if (!els.legacyUpdateBanner) return;
            els.legacyUpdateBanner.classList.remove('hidden');
            els.legacyUpdateBannerTitle.textContent = 'Updating FlashYT...';
            els.legacyUpdateBannerText.textContent = message.message || 'Please wait while we update your native host.';
            if (els.legacyUpdateBannerCopyBtn) {
                els.legacyUpdateBannerCopyBtn.disabled = message.status === 'started';
                if (message.status === 'started') {
                    els.legacyUpdateBannerCopyBtn.textContent = 'Updating...';
                } else if (message.status === 'done') {
                    els.legacyUpdateBannerCopyBtn.textContent = 'Done!';
                } else if (message.status === 'error') {
                    els.legacyUpdateBannerCopyBtn.textContent = 'Retry Update';
                    els.legacyUpdateBannerCopyBtn.disabled = false;
                }
            }
        }
    });

    if (els.legacyUpdateBannerOpenBtn) {
        els.legacyUpdateBannerOpenBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: "OPEN_UPDATE_LINK", url: updateOpenUrl }, () => chrome.runtime.lastError);
        });
    }

    if (els.legacyUpdateBannerCopyBtn) {
        els.legacyUpdateBannerCopyBtn.addEventListener('click', async () => {
            if (els.legacyUpdateBannerCopyBtn._isSelfUpdate) {
                els.legacyUpdateBannerCopyBtn.disabled = true;
                els.legacyUpdateBannerCopyBtn.textContent = 'Starting...';
                chrome.runtime.sendMessage({ type: "SELF_UPDATE" }, (res) => {
                    if (chrome.runtime.lastError || !res?.ok) {
                        els.legacyUpdateBannerCopyBtn.disabled = false;
                        els.legacyUpdateBannerCopyBtn.textContent = 'Update Failed';
                        setTimeout(() => { renderUpdateBanner(); }, 2000);
                    }
                });
                return;
            }
            const cmd = els.legacyUpdateBannerCopyBtn._flashytCmd || updateCopyCommand || "";
            const ok = await copyText(cmd);
            const old = els.legacyUpdateBannerCopyBtn.textContent;
            els.legacyUpdateBannerCopyBtn.textContent = ok ? "Copied!" : "Copy Failed";
            setTimeout(() => { els.legacyUpdateBannerCopyBtn.textContent = old; }, 1400);
        });
    }

    // ── Update Banner Logic ──────────────────────────────────────
    async function initUpdateBanner() {
        const stored = await chrome.storage.local.get([
            'update_available',
            'update_version',
            'update_release_url'
        ]);

        if (!stored.update_available) {
            // No update — keep banner hidden, nothing to do
            return;
        }

        // Show the banner
        const banner = document.getElementById('update-banner');
        if (banner) banner.style.display = 'block';

        // Fill in the version label
        const versionLabel = document.getElementById('update-version-label');
        if (versionLabel && stored.update_version) {
            versionLabel.textContent = 'v' + stored.update_version;
        }

        // Set the manual download fallback link
        const manualLink = document.getElementById('update-manual-link');
        if (manualLink && stored.update_release_url) {
            manualLink.href = stored.update_release_url;
        }

        // Wire up the Update button
        const updateBtn = document.getElementById('update-btn');
        if (updateBtn) {
            updateBtn.addEventListener('click', handleUpdateClick);
        }
    }

    async function handleUpdateClick() {
        // Disable button immediately to prevent double-clicks
        const updateBtn = document.getElementById('update-btn');
        if (updateBtn) {
            updateBtn.disabled = true;
            updateBtn.textContent = 'Starting...';
        }

        // Switch to "installing" state
        showUpdateState('installing');

        try {
            // Send update command to background.js, which forwards to host.exe
            const response = await chrome.runtime.sendMessage({ type: 'TRIGGER_UPDATE' });

            if (response && response.type === 'update_done') {
                // Success — show done state
                showUpdateState('done');
                // Clear the update flag from storage so banner doesn't show on next open
                await chrome.storage.local.set({ update_available: false });
            } else if (response && response.type === 'update_error') {
                // Host reported an error
                showUpdateState('error', response.message || 'Update failed. Please download manually.');
            } else if (!response) {
                // No response — host may have exited. Treat as success.
                showUpdateState('done');
                await chrome.storage.local.set({ update_available: false });
            } else {
                showUpdateState('error', 'Unexpected response. Please download manually.');
            }
        } catch (error) {
            // chrome.runtime.sendMessage throws if background disconnects
            if (error.message && error.message.includes('disconnected')) {
                showUpdateState('done');
                await chrome.storage.local.set({ update_available: false });
            } else {
                showUpdateState('error', 'Could not reach update service. Please download manually.');
            }
        }
    }

    function showUpdateState(state, errorMessage) {
        // Hide all states first
        const states = ['available', 'installing', 'done', 'error'];
        states.forEach(s => {
            const el = document.getElementById('update-' + s);
            if (el) el.style.display = 'none';
        });

        // Show the requested state
        const target = document.getElementById('update-' + state);
        if (target) {
            target.style.display = 'flex';
        }

        // Set error message if provided
        if (state === 'error' && errorMessage) {
            const errorText = document.getElementById('update-error-text');
            if (errorText) {
                errorText.textContent = errorMessage;
            }
        }
    }
    // ── End Update Banner Logic ──────────────────────────────────

    chrome.storage.local.get(['banner_dismissed_notice_shown'], function (result) {
        if (!result.banner_dismissed_notice_shown) {
            const notice = document.getElementById('banner-notice');
            if (notice) notice.style.display = 'block';
            chrome.storage.local.set({ banner_dismissed_notice_shown: true });
        }
    });

    initUpdateBanner();

    // Initial check
    fetchDownloads();
    checkHost();
    fetchUpdateStatus();
    let updateTick = 0;
    // Downloads poll: every 1s for smooth progress bars
    setInterval(() => {
        fetchDownloads();
        updateTick += 1;
        // Host status: every 5s (it's slow, no need to thrash every second)
        if (updateTick % 5 === 0) checkHost();
        // Release update: every 100s (~1.5 min)
        if (updateTick % 100 === 0) fetchUpdateStatus();
    }, 1000);
});
