// ==UserScript==
// @name         One-Click YouTube Downloader
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Adds a download button to YouTube videos that communicates with a local Flask server to trigger downloads.
// @author       You
// @match        *://*.youtube.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function () {
    'use strict';

    const SERVER_URL = 'http://127.0.0.1:5000/download';
    const STATUS_URL = 'http://127.0.0.1:5000/status';
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

    function injectButton() {
        if (!window.location.href.includes('watch?v=')) return false;
        if (document.getElementById('yt-downloader-btn')) return true; // Already injected

        // YouTube changes these IDs constantly. We check all of them.
        const possibleTargets = [
            { selector: 'ytd-watch-metadata', position: 'prepend' }, // Best spot, right under video
            { selector: '#owner-inner', position: 'append' },
            { selector: '#top-row.ytd-watch-metadata', position: 'append' },
            { selector: '#owner.ytd-watch-metadata', position: 'append' },
            { selector: '#actions.ytd-watch-metadata', position: 'append' },
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
