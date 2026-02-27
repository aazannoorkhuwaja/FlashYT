/**
 * @jest-environment jsdom
 */

const fs = require('fs');
const path = require('path');

// Load the content script text
const scriptPath = path.resolve(__dirname, '../content_script.js');
const scriptCode = fs.readFileSync(scriptPath, 'utf8');

describe('FlashYT UI Component Tests (content_script.js)', () => {
    let runtimeListener = null;

    beforeEach(() => {
        // Reset JSDOM
        document.body.innerHTML = '<div id="owner" class="ytd-watch-metadata"></div>';

        // Mock the Chrome API Extension runtime
        global.chrome = {
            runtime: {
                sendMessage: jest.fn(),
                onMessage: {
                    addListener: jest.fn((cb) => {
                        runtimeListener = cb;
                    })
                }
            }
        };

        // Inject the script manually to populate global functions (injectButton, closeModal)
        eval(scriptCode);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('injectButton() safely inserts FlashYT downloader button to the DOM', () => {
        injectButton();
        const btnContainer = document.getElementById('ytdl-native-btn-container');
        const btn = document.getElementById('ytdl-native-btn');

        expect(btnContainer).not.toBeNull();
        expect(btn).not.toBeNull();
        expect(btn.innerHTML).toContain('Download');
        expect(btn.dataset.state).toBe('idle');
    });

    test('openModal() generates and displays the quality selection overlay', () => {
        openModal();
        const overlay = document.getElementById('flashyt-modal-overlay');
        const modal = document.getElementById('flashyt-modal');

        expect(overlay).not.toBeNull();
        expect(modal).not.toBeNull();
        expect(overlay.style.display).toBe('flex');
        expect(overlay.style.opacity).toBe('1');
    });

    test('closeModal() removes opacity and smoothly triggers teardown', () => {
        openModal();
        const overlay = document.getElementById('flashyt-modal-overlay');
        expect(overlay.style.opacity).toBe('1');

        closeModal();
        // Modal transitions to 0 before CSS handles the full display hide
        expect(overlay.style.opacity).toBe('0');
    });

    test('showToast() correctly renders the temporary notification bubble', () => {
        showToast("Download Saved!");

        // The toast should exist in the DOM
        const toast = document.querySelector('.flashyt-toast');
        expect(toast).not.toBeNull();
        expect(toast.textContent).toBe("Download Saved!");

        // Since it's a success toast, it should not have the error class
        expect(toast.classList.contains('flashyt-toast-error')).toBe(false);
    });

    test('progress message updates button state and text', () => {
        injectButton();
        startDownload({ itag: 'video_720', real_itag: 22, size_mb: 1.2, label: '720p' }, 'Test Video', 'abc123xyz00');
        runtimeListener({
            type: 'progress',
            downloadId: currentDownloadId,
            videoId: 'abc123xyz00',
            percent: '42%',
            speed: '1.2MiB/s'
        });
        const btn = document.getElementById('ytdl-native-btn');
        expect(btn.textContent).toContain('42%');
        expect(btn.dataset.state).toBe('busy');
    });

    test('control ack pause then paused then resume updates button state', () => {
        injectButton();
        startDownload({ itag: 'video_720', real_itag: 22, size_mb: 1.2, label: '720p' }, 'Test Video', 'abc123xyz00');

        runtimeListener({ type: 'control_ack', action: 'pause', ok: true, downloadId: currentDownloadId });
        let btn = document.getElementById('ytdl-native-btn');
        expect(btn.dataset.state).toBe('busy');

        runtimeListener({ type: 'paused', downloadId: currentDownloadId });
        btn = document.getElementById('ytdl-native-btn');
        expect(btn.dataset.state).toBe('paused');

        runtimeListener({ type: 'control_ack', action: 'resume', ok: true, downloadId: currentDownloadId });
        btn = document.getElementById('ytdl-native-btn');
        expect(btn.dataset.state).toBe('busy');
    });

    test('cancelled message resets button to idle', () => {
        injectButton();
        startDownload({ itag: 'video_720', real_itag: 22, size_mb: 1.2, label: '720p' }, 'Test Video', 'abc123xyz00');
        runtimeListener({ type: 'cancelled', downloadId: currentDownloadId, videoId: 'abc123xyz00' });
        const btn = document.getElementById('ytdl-native-btn');
        expect(btn.dataset.state).toBe('idle');
    });
});
