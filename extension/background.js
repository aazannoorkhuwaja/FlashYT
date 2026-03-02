const HOST_NAME = "com.youtube.native.ext";
const MIN_REQUIRED_HOST_VERSION = "2.0.4";
const GITHUB_RELEASE_API = "https://api.github.com/repos/aazannoorkhuwaja/FlashYT/releases/latest";
const GITHUB_RELEASES_URL = "https://github.com/aazannoorkhuwaja/FlashYT/releases/latest";
const UPDATE_ALARM_NAME = "flashyt_update_check";
const UPDATE_CHECK_INTERVAL_MIN = 180;
const UPDATE_CACHE_MS = 15 * 60 * 1000;

let nativePort = null;
let hostConnected = false;
let keepAliveTimer = null;
let hostVersion = null;
let hostUpdateRequired = false;
let updateFetchInFlight = null;
let updateState = {
  checkedAt: 0,
  latestVersion: null,
  releaseUrl: GITHUB_RELEASES_URL,
  updateAvailable: false,
  error: null,
};

const formatCache = new Map();
const CACHE_MAX = 50;
const CACHE_TTL_MS = 10 * 60 * 1000;
const prefetchInflight = new Map();
const PREFETCH_TIMEOUT_MS = 60000;

function normalizeVersion(raw) {
  const src = (raw || "").toString().trim().replace(/^v/i, "");
  const core = src.split("-")[0];
  const parts = core.split(".").map((p) => parseInt(p, 10));
  if (parts.some((p) => Number.isNaN(p))) return [0, 0, 0];
  while (parts.length < 3) parts.push(0);
  return parts.slice(0, 3);
}

function compareVersions(a, b) {
  const va = normalizeVersion(a);
  const vb = normalizeVersion(b);
  for (let i = 0; i < 3; i += 1) {
    if (va[i] > vb[i]) return 1;
    if (va[i] < vb[i]) return -1;
  }
  return 0;
}

function getPlatform() {
  const p = (navigator.userAgentData?.platform || navigator.platform || navigator.userAgent || "").toLowerCase();
  if (p.includes("win")) return "windows";
  if (p.includes("mac")) return "macos";
  return "linux";
}

function getHostUpdateGuidance() {
  const platform = getPlatform();
  if (platform === "windows") {
    return {
      updateUrl: GITHUB_RELEASES_URL,
      updateLabel: "Download FlashYT Setup",
      updateCommand: null,
    };
  }
  return {
    updateUrl: GITHUB_RELEASES_URL,
    updateLabel: "Open Update Guide",
    updateCommand: "curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh | bash",
  };
}

function getHostStatusPayload() {
  const guidance = getHostUpdateGuidance();
  const status = hostUpdateRequired
    ? "update_required"
    : hostConnected
      ? "connected"
      : "disconnected";
  return {
    status,
    host_version: hostVersion,
    min_required_host_version: MIN_REQUIRED_HOST_VERSION,
    update_required: hostUpdateRequired,
    ...guidance,
  };
}

function broadcastUpdateStatus() {
  const payload = {
    type: "UPDATE_STATUS",
    host: getHostStatusPayload(),
    release: updateState,
  };
  chrome.runtime.sendMessage(payload, () => chrome.runtime.lastError);
}

function handleNativeMessage(response) {
  if (response.type === "ping") {
    if (!hostConnected || hostVersion !== response.version) {
      markHostCompatibility(response.version);
    }
    return;
  }
}

async function refreshUpdateState(force = false) {
  if (!force && Date.now() - (updateState.checkedAt || 0) < UPDATE_CACHE_MS) {
    return updateState;
  }
  if (updateFetchInFlight) return updateFetchInFlight;

  updateFetchInFlight = (async () => {
    try {
      const resp = await fetch(GITHUB_RELEASE_API);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const latest = (data.tag_name || "").replace(/^v/i, "");
      const current = chrome.runtime.getManifest().version;

      updateState = {
        checkedAt: Date.now(),
        latestVersion: latest,
        releaseUrl: data.html_url || GITHUB_RELEASES_URL,
        updateAvailable: compareVersions(current, latest) < 0,
        error: null,
      };
    } catch (err) {
      console.error("[Background] Update check failed:", err);
      updateState.error = err.message;
      updateState.checkedAt = Date.now();
    } finally {
      updateFetchInFlight = null;
    }
    broadcastUpdateStatus();
    return updateState;
  })();

  return updateFetchInFlight;
}

function connectToNativeHost() {
  if (nativePort) return;
  try {
    nativePort = chrome.runtime.connectNative(HOST_NAME);
    // CRITICAL: We don't set hostConnected = true here anymore.
    // We wait for the first successful ping response.
    nativePort.onMessage.addListener(handleNativeMessage);
    nativePort.onDisconnect.addListener(() => {
      console.warn("[Background] Native host disconnected.");
      nativePort = null;
      hostConnected = false;
      hostVersion = null;
      stopKeepAlive();
      broadcastUpdateStatus();
    });
    // Immediately ping to verify the connection
    nativePort.postMessage({ type: "ping" });
    startKeepAlive();
  } catch (err) {
    console.error("[Background] Failed to connect to native host:", err);
    nativePort = null;
    hostConnected = false;
    broadcastUpdateStatus();
  }
}

function scheduleUpdateChecks() {
  chrome.alarms.create(UPDATE_ALARM_NAME, { periodInMinutes: UPDATE_CHECK_INTERVAL_MIN });
}

function sendToYouTubeTabs(payload) {
  chrome.tabs.query({ url: "https://www.youtube.com/*" }, (tabs) => {
    tabs.forEach((tab) => {
      chrome.tabs.sendMessage(tab.id, payload, () => chrome.runtime.lastError);
    });
  });
}

function startKeepAlive() {
  if (keepAliveTimer) return;
  keepAliveTimer = setInterval(() => {
    if (nativePort && hostConnected) {
      nativePort.postMessage({ type: "ping" });
    } else {
      stopKeepAlive();
    }
  }, 20000);
}

function stopKeepAlive() {
  if (!keepAliveTimer) return;
  clearInterval(keepAliveTimer);
  keepAliveTimer = null;
}

function markHostCompatibility(version) {
  const normalized = (version || "").toString().trim();
  hostVersion = normalized || "legacy";
  hostUpdateRequired = compareVersions(hostVersion, MIN_REQUIRED_HOST_VERSION) < 0;
  hostConnected = !hostUpdateRequired;

  if (hostUpdateRequired) {
    const guidance = getHostUpdateGuidance();
    sendToYouTubeTabs({
      type: "HOST_UPDATE_REQUIRED",
      hostVersion,
      minRequiredVersion: MIN_REQUIRED_HOST_VERSION,
      updateUrl: guidance.updateUrl,
      updateCommand: guidance.updateCommand,
      message: `FlashYT host ${hostVersion} is outdated. Update to ${MIN_REQUIRED_HOST_VERSION}+ to continue.`,
    });
  }
  broadcastUpdateStatus();
}

function clearPrefetchInflight(reason) {
  prefetchInflight.forEach((entry) => {
    if (entry.timer) clearTimeout(entry.timer);
    if (nativePort && entry.listener) nativePort.onMessage.removeListener(entry.listener);
    const payload = { type: "error", message: reason || "Prefetch failed." };
    (entry.responders || []).forEach((respond) => {
      try { respond(payload); } catch (_) { }
    });
  });
  prefetchInflight.clear();
}

class DownloadManager {
  constructor() {
    this.downloads = {};
    this.maxConcurrent = 3;
    this.restoreState();
    this.loadSettings();
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "local" || !changes.max_concurrent) return;
      this.maxConcurrent = this._normalizeConcurrent(changes.max_concurrent.newValue);
      this.processQueue();
    });
  }

  restoreState() {
    chrome.storage.local.get(["active_downloads"], (result) => {
      this.downloads = result.active_downloads || {};
      this.processQueue();
    });
  }

  loadSettings() {
    chrome.storage.local.get({ max_concurrent: 3 }, (result) => {
      this.maxConcurrent = this._normalizeConcurrent(result.max_concurrent);
      this.processQueue();
    });
  }

  _normalizeConcurrent(rawValue) {
    const parsed = parseInt(rawValue, 10);
    if (Number.isNaN(parsed)) return 3;
    return Math.min(10, Math.max(1, parsed));
  }

  activeCount() {
    return Object.values(this.downloads).filter((d) => ["downloading", "starting", "pausing", "resuming", "cancelling"].includes(d.status)).length;
  }

  queueDownload(id, pendingAction = "start") {
    const dl = this.downloads[id];
    if (!dl) return;
    dl.status = "queued";
    dl.pendingAction = pendingAction;
    dl.speed = 0;
    delete dl.prevStatus;
    this.saveState();
  }

  processQueue() {
    executeWithHost(
      () => {
        let slots = this.maxConcurrent - this.activeCount();
        if (slots <= 0) return;

        const queued = Object.values(this.downloads).filter((d) => d.status === "queued");
        for (const dl of queued) {
          if (slots <= 0) break;
          if (dl.pendingAction === "resume") {
            this.markActionRequested(dl.id, "resume");
            nativePort.postMessage({ type: "resume", downloadId: dl.id });
          } else {
            this.startNativeDownload(dl);
          }
          slots -= 1;
        }
      },
      () => { }
    );
  }

  saveState() {
    chrome.storage.local.set({ active_downloads: this.downloads });
    chrome.runtime.sendMessage({ type: "DOWNLOADS_UPDATED", downloads: Object.values(this.downloads) }, () => chrome.runtime.lastError);
  }

  findDownload(payload) {
    if (payload.downloadId && this.downloads[payload.downloadId]) return this.downloads[payload.downloadId];
    if (payload.videoId) return Object.values(this.downloads).find((d) => d.videoId === payload.videoId);
    return null;
  }

  addDownload(videoInfo, url, filename, providedId = null) {
    const downloadId = providedId || `${videoInfo.videoId || Date.now()}_${videoInfo.quality || "auto"}`;
    this.downloads[downloadId] = {
      id: downloadId,
      videoId: videoInfo.videoId,
      title: videoInfo.title,
      thumbnail: videoInfo.thumbnail,
      quality: videoInfo.quality,
      real_itag: videoInfo.real_itag,
      format: videoInfo.format || "MP4",
      totalSize: videoInfo.totalSize || 0,
      downloaded: 0,
      progress: 0,
      speed: 0,
      status: "queued",
      pendingAction: "start",
      url,
      filename,
    };

    this.saveState();
    this.processQueue();
    return downloadId;
  }

  startNativeDownload(download) {
    if (!download) return;
    download.status = "starting";
    download.pendingAction = null;
    delete download.prevStatus;
    this.saveState();

    executeWithHost(
      () => {
        chrome.storage.local.get({ save_location: "~/Downloads" }, (res) => {
          nativePort.postMessage({
            type: "download",
            url: download.url,
            itag: download.quality,
            real_itag: download.real_itag,
            title: download.title,
            videoId: download.videoId,
            downloadId: download.id,
            save_location: res.save_location,
          });
          startKeepAlive();
        });
      },
      () => {
        download.status = "error";
        download.pendingAction = null;
        this.saveState();
        this.processQueue();
      }
    );
  }

  updateProgress(payload) {
    const dl = this.findDownload(payload);
    if (!dl) return;

    const pct = parseFloat((payload.percent || "").toString().replace("%", ""));
    if (!Number.isNaN(pct)) {
      dl.progress = Math.max(dl.progress || 0, pct);
    }

    if (payload.speed && typeof payload.speed === "string") {
      const match = payload.speed.match(/([\d.]+)\s*(KiB|MiB|GiB)/);
      if (match) {
        const val = parseFloat(match[1]);
        const unit = match[2];
        let bytes = val;
        if (unit === "KiB") bytes *= 1024;
        if (unit === "MiB") bytes *= 1048576;
        if (unit === "GiB") bytes *= 1073741824;
        dl.speed = bytes;
      }
    }

    if (dl.totalSize > 0) {
      dl.downloaded = Math.round(dl.totalSize * (dl.progress / 100));
    }

    dl.status = "downloading";
    dl.pendingAction = null;
    delete dl.prevStatus;
    this.saveState();
  }

  markTerminal(payload) {
    const dl = this.findDownload(payload);
    if (!dl) return;

    if (payload.type === "cancelled") {
      delete this.downloads[dl.id];
      this.saveState();
      this.processQueue();
      return;
    }

    dl.status = payload.type === "error" ? "error" : "completed";
    dl.pendingAction = null;
    delete dl.prevStatus;
    dl.speed = 0;
    if (payload.type === "done") dl.progress = 100;

    if (payload.type === "done") {
      chrome.storage.local.get({ history: [] }, (data) => {
        const history = [{
          videoId: dl.videoId,
          title: dl.title,
          thumbnail: dl.thumbnail,
          filename: payload.filename || dl.filename,
          size_mb: payload.size_mb || 0,
          actual_quality: payload.actual_quality || '',
          path: payload.path || "",
          already_exists: !!payload.already_exists,
          time: Date.now(),
        }, ...data.history].slice(0, 50);
        chrome.storage.local.set({ history });
      });

      if (chrome.notifications) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: payload.already_exists ? "⚡ FlashYT – Already Downloaded" : "⚡ FlashYT – Download Complete",
          message: payload.filename || "Video ready.",
        });
      }
    }

    this.saveState();
    this.processQueue();
    if (!Object.values(this.downloads).some((d) => ["downloading", "starting", "pausing", "resuming", "cancelling"].includes(d.status))) {
      stopKeepAlive();
    }
  }

  pauseDownload(id) {
    const dl = this.downloads[id];
    if (!dl) return;
    dl.status = "paused";
    dl.speed = 0;
    dl.pendingAction = null;
    delete dl.prevStatus;
    this.saveState();
    this.processQueue();
  }

  resumeDownload(id) {
    const dl = this.downloads[id];
    if (!dl) return;
    dl.status = "starting";
    dl.pendingAction = null;
    delete dl.prevStatus;
    this.saveState();
  }

  cancelDownload(id) {
    if (!this.downloads[id]) return;
    delete this.downloads[id];
    this.saveState();
    this.processQueue();
  }

  markActionRequested(id, action) {
    const dl = this.downloads[id];
    if (!dl) return;
    dl.prevStatus = dl.status;
    dl.pendingAction = action;
    if (action === "pause") dl.status = "pausing";
    if (action === "resume") dl.status = "resuming";
    if (action === "cancel") dl.status = "cancelling";
    if (action !== "cancel") dl.speed = 0;
    this.saveState();
  }

  markActionFailed(id, action, message) {
    const dl = this.downloads[id];
    if (!dl) return;
    dl.pendingAction = null;
    dl.status = dl.prevStatus || dl.status || "downloading";
    delete dl.prevStatus;
    dl.last_error = message || "";
    this.saveState();
    this.processQueue();
  }

  handleControlAck(payload) {
    if (!payload.downloadId) return;
    if (!payload.ok) {
      this.markActionFailed(payload.downloadId, payload.action, payload.message);
      return;
    }

    const msg = (payload.message || "").toLowerCase();
    if (payload.action === "pause" && msg.includes("already paused")) {
      this.pauseDownload(payload.downloadId);
      return;
    }
    if (payload.action === "resume" && msg.includes("resume queued")) {
      this.queueDownload(payload.downloadId, "resume");
      this.processQueue();
      return;
    }
    if (payload.action === "resume" && msg.includes("already active")) {
      const dl = this.downloads[payload.downloadId];
      if (dl) {
        dl.status = "downloading";
        dl.pendingAction = null;
        delete dl.prevStatus;
        this.saveState();
      }
      return;
    }
    if (payload.action === "cancel" && (msg.includes("already inactive") || msg.includes("cancel requested"))) {
      this.cancelDownload(payload.downloadId);
      return;
    }

    // Final state transition is driven by host terminal messages.
    // Here we only keep transitional status aligned until that arrives.
    this.markActionRequested(payload.downloadId, payload.action);
  }

  clearCompleted() {
    Object.keys(this.downloads).forEach((id) => {
      const s = this.downloads[id].status;
      if (s === "completed" || s === "error" || s === "cancelled") delete this.downloads[id];
    });
    this.saveState();
  }
}

const manager = new DownloadManager();

function connectToHost() {
  if (nativePort) return;
  nativePort = chrome.runtime.connectNative(HOST_NAME);

  nativePort.onMessage.addListener((rawResponse) => {
    let response = rawResponse;
    if (!response.type) {
      if (response.error) response = { type: "error", message: response.error, ...response };
      else if (response.filename || response.path) response = { type: "done", ...response };
    }

    if (response.type === "pong") {
      markHostCompatibility(response.version);
      if (hostConnected) manager.processQueue();
      refreshUpdateState(false);
      return;
    }

    if (response.type === "self_update_progress") {
      sendToYouTubeTabs(response);
      chrome.runtime.sendMessage(response, () => chrome.runtime.lastError);
      return;
    }

    const isDownloadError = response.type === "error" && (response.downloadId || response.videoId);

    if (response.type === "progress") manager.updateProgress(response);
    if (response.type === "done" || response.type === "cancelled" || isDownloadError) manager.markTerminal(response);
    if (response.type === "paused") manager.pauseDownload(response.downloadId);
    if (response.type === "control_ack") manager.handleControlAck(response);

    if (["progress", "done", "cancelled", "paused", "control_ack"].includes(response.type) || isDownloadError) {
      sendToYouTubeTabs(response);
    }
  });

  nativePort.onDisconnect.addListener(() => {
    const errMsg = chrome.runtime.lastError?.message || "";
    const notInstalled = errMsg.includes("not found") || errMsg.includes("cannot be found");
    if (notInstalled) sendToYouTubeTabs({ type: "HOST_NOT_INSTALLED" });
    nativePort = null;
    hostConnected = false;
    hostVersion = null;
    hostUpdateRequired = false;
    broadcastUpdateStatus();
    clearPrefetchInflight("Host disconnected during format fetch.");
  });

  nativePort.postMessage({ type: "ping" });
}

function executeWithHost(onSuccess, onError) {
  if (hostUpdateRequired) {
    const guidance = getHostUpdateGuidance();
    if (onError) {
      onError({
        code: "HOST_UPDATE_REQUIRED",
        message: `Host update required (installed: ${hostVersion || "unknown"}, required: ${MIN_REQUIRED_HOST_VERSION}+).`,
        hostVersion,
        minRequiredVersion: MIN_REQUIRED_HOST_VERSION,
        ...guidance,
      });
    }
    return;
  }
  if (!nativePort || !hostConnected) {
    connectToHost();
    setTimeout(() => {
      if (hostConnected) onSuccess();
      else if (onError) {
        if (hostUpdateRequired) {
          const guidance = getHostUpdateGuidance();
          onError({
            code: "HOST_UPDATE_REQUIRED",
            message: `Host update required (installed: ${hostVersion || "unknown"}, required: ${MIN_REQUIRED_HOST_VERSION}+).`,
            hostVersion,
            minRequiredVersion: MIN_REQUIRED_HOST_VERSION,
            ...guidance,
          });
        } else {
          onError({ code: "HOST_NOT_CONNECTED", message: "Host not connected." });
        }
      }
    }, 350);
    return;
  }
  onSuccess();
}

function cacheSet(url, value) {
  if (formatCache.size >= CACHE_MAX) {
    formatCache.delete(formatCache.keys().next().value);
  }
  formatCache.set(url, { value, ts: Date.now() });
}

function hasRealQualityData(response) {
  if (!response || !Array.isArray(response.qualities) || response.qualities.length === 0) return false;
  return response.qualities.some((q) => q && q.real_itag !== null && q.real_itag !== undefined && q.real_itag !== "");
}

function cacheGet(url) {
  const entry = formatCache.get(url);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL_MS) {
    formatCache.delete(url);
    return null;
  }
  if (entry.value?.degraded || !hasRealQualityData(entry.value)) {
    formatCache.delete(url);
    return null;
  }
  return entry.value;
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "download_youtube",
    title: "⚡ Download with FlashYT",
    contexts: ["link"],
    targetUrlPatterns: ["https://www.youtube.com/watch*", "https://youtube.com/watch*"],
  });
  scheduleUpdateChecks();
  refreshUpdateState(true);
});

chrome.runtime.onStartup.addListener(() => {
  scheduleUpdateChecks();
  refreshUpdateState(false);
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === UPDATE_ALARM_NAME) refreshUpdateState(true);
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "download_youtube") return;
  const linkUrl = info.linkUrl || "";
  const videoIdMatch = linkUrl.match(/[?&]v=([A-Za-z0-9_-]{11})/);
  const videoId = videoIdMatch ? videoIdMatch[1] : null;
  const downloadId = `dl_ctx_${Date.now()}`;
  executeWithHost(
    () => {
      chrome.storage.local.get({ save_location: "~/Downloads" }, (res) => {
        nativePort.postMessage({
          type: "download",
          url: linkUrl,
          itag: "video_1080",
          real_itag: null,
          title: "YouTube Video",
          videoId: videoId || "",
          downloadId,
          save_location: res.save_location,
        });
        manager.downloads[downloadId] = {
          id: downloadId,
          videoId: videoId || "",
          title: "YouTube Video",
          thumbnail: videoId ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` : "",
          quality: "video_1080",
          real_itag: null,
          format: "MP4",
          totalSize: 0,
          downloaded: 0,
          progress: 0,
          speed: 0,
          status: "starting",
          pendingAction: null,
          url: linkUrl,
          filename: "YouTube Video.mp4",
        };
        manager.saveState();
        startKeepAlive();
      });
    },
    () => {
      if (chrome.notifications) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: "FlashYT Not Running",
          message: "Run the FlashYT installer and try again.",
        });
      }
    }
  );
});

function processMessage(request, sendResponse) {
  if (request.type === "GET_UPDATE_STATUS") {
    sendResponse({
      host: getHostStatusPayload(),
      release: updateState,
    });
    refreshUpdateState(false);
    return false;
  }

  if (request.type === "OPEN_UPDATE_LINK") {
    const guidance = getHostUpdateGuidance();
    const targetUrl = request.url || guidance.updateUrl || GITHUB_RELEASES_URL;
    chrome.tabs.create({ url: targetUrl }, () => chrome.runtime.lastError);
    sendResponse({ ok: true });
    return false;
  }

  if (request.type === "SELF_UPDATE") {
    if (!nativePort || !hostConnected) {
      sendResponse({ ok: false, message: "Host not connected" });
      return false;
    }
    nativePort.postMessage({ type: "self_update" });
    sendResponse({ ok: true });
    return false;
  }

  if (request.type === "PREFETCH") {
    const url = request.url;
    if (!request.force) {
      const cached = cacheGet(url);
      if (cached) {
        sendResponse(cached);
        return false;
      }
    } else {
      formatCache.delete(url);
    }

    const existing = prefetchInflight.get(url);
    if (existing) {
      existing.responders.push(sendResponse);
      return true;
    }

    const responders = [sendResponse];
    let settled = false;
    const finalize = (payload) => {
      if (settled) return;
      settled = true;
      const entry = prefetchInflight.get(url);
      if (entry?.timer) clearTimeout(entry.timer);
      if (nativePort && entry?.listener) nativePort.onMessage.removeListener(entry.listener);
      prefetchInflight.delete(url);
      responders.forEach((respond) => {
        try { respond(payload); } catch (_) { }
      });
    };

    const listener = (response) => {
      const sameReq = !response.reqUrl || response.reqUrl === url;
      if (!sameReq) return;

      if (response.type === "prefetch_result") {
        if (!response.degraded && hasRealQualityData(response)) cacheSet(url, response);
        finalize(response);
        return;
      }

      const isPrefetchError = response.type === "prefetch_error" || (response.type === "error" && !!response.reqUrl);
      if (!isPrefetchError) return;
      finalize({ type: "error", message: response.message || "Could not fetch qualities." });
    };

    const timer = setTimeout(() => {
      finalize({ type: "error", message: "Still fetching formats. Please try again in a few seconds." });
    }, PREFETCH_TIMEOUT_MS);

    prefetchInflight.set(url, { responders, listener, timer });

    if (!nativePort) {
      finalize({ type: "error", message: "Host not connected. Please wait a moment and try again." });
      return true;
    }
    nativePort.onMessage.addListener(listener);
    nativePort.postMessage({ type: "prefetch", url });
    return true;
  }

  if (request.type === "DOWNLOAD") {
    const downloadId = manager.addDownload({
      title: request.title,
      videoId: request.videoId,
      thumbnail: request.thumbnail,
      quality: request.itag,
      real_itag: request.real_itag,
      format: request.format || "MP4",
      totalSize: parseFloat(request.size_mb || 0) * 1048576,
    }, request.url, `${request.title}.mp4`, request.downloadId);
    const status = manager.downloads[downloadId]?.status || "queued";
    sendResponse({ status, downloadId });
    return false;
  }

  if (request.type === "START_DOWNLOAD") {
    const downloadId = manager.addDownload(request.videoInfo, request.url, request.filename, request.downloadId);
    sendResponse({ success: true, downloadId, status: manager.downloads[downloadId]?.status || "queued" });
    return false;
  }

  if (request.type === "GET_DOWNLOAD_STATE") {
    const download = Object.values(manager.downloads).find((d) => d.videoId === request.videoId && ["queued", "starting", "downloading", "paused", "pausing", "resuming", "cancelling"].includes(d.status));
    if (!download) {
      sendResponse({ active: false });
      return false;
    }
    sendResponse({ active: true, status: download.status, percent: `${download.progress}%`, downloadId: download.id, speed: download.speed });
    return false;
  }

  if (request.type === "GET_DOWNLOADS") {
    sendResponse({ downloads: Object.values(manager.downloads) });
    return false;
  }

  if (request.type === "CLEAR_COMPLETED") {
    manager.clearCompleted();
    sendResponse({ success: true });
    return false;
  }

  if (request.type === "PAUSE_DOWNLOAD") {
    const target = manager.downloads[request.id];
    if (!target) {
      sendResponse({ success: false, error: "NOT_FOUND" });
      return false;
    }
    if (target.status === "queued") {
      target.status = "paused";
      target.pendingAction = "resume";
      target.speed = 0;
      manager.saveState();
      sendResponse({ success: true });
      return false;
    }
    if (target.status === "paused") {
      sendResponse({ success: true });
      return false;
    }
    manager.markActionRequested(request.id, "pause");
    executeWithHost(
      () => {
        nativePort.postMessage({ type: "pause", downloadId: request.id });
        sendResponse({ success: true });
      },
      () => {
        manager.markActionFailed(request.id, "pause", "Host not connected.");
        sendResponse({ success: false, error: "HOST_NOT_CONNECTED" });
      }
    );
    return true;
  }

  if (request.type === "RESUME_DOWNLOAD") {
    const target = manager.downloads[request.id];
    if (!target) {
      sendResponse({ success: false, error: "NOT_FOUND" });
      return false;
    }
    if (manager.activeCount() >= manager.maxConcurrent) {
      manager.queueDownload(request.id, "resume");
      sendResponse({ success: true, queued: true });
      return false;
    }
    manager.markActionRequested(request.id, "resume");
    executeWithHost(
      () => {
        nativePort.postMessage({ type: "resume", downloadId: request.id });
        sendResponse({ success: true });
      },
      () => {
        manager.markActionFailed(request.id, "resume", "Host not connected.");
        sendResponse({ success: false, error: "HOST_NOT_CONNECTED" });
      }
    );
    return true;
  }

  if (request.type === "CANCEL_DOWNLOAD") {
    const target = manager.downloads[request.id];
    if (!target) {
      sendResponse({ success: false, error: "NOT_FOUND" });
      return false;
    }
    if (target.status === "queued" || target.status === "paused") {
      manager.cancelDownload(request.id);
      sendResponse({ success: true });
      return false;
    }
    manager.markActionRequested(request.id, "cancel");
    executeWithHost(
      () => {
        nativePort.postMessage({ type: "cancel", downloadId: request.id });
        sendResponse({ success: true });
      },
      () => {
        manager.markActionFailed(request.id, "cancel", "Host not connected.");
        sendResponse({ success: false, error: "HOST_NOT_CONNECTED" });
      }
    );
    return true;
  }

  if (request.type === "OPEN_FOLDER") {
    if (nativePort) nativePort.postMessage({ type: "open_folder", path: request.path || "" });
    sendResponse({ status: "ok" });
    return false;
  }

  sendResponse({ error: "UNKNOWN_REQUEST_TYPE" });
  return false;
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.type === "CHECK_STATUS") {
    if (hostConnected || hostUpdateRequired) {
      sendResponse(getHostStatusPayload());
      return false;
    }
    let responded = false;
    const respondStatus = () => {
      if (responded) return;
      responded = true;
      sendResponse(getHostStatusPayload());
    };
    executeWithHost(
      () => respondStatus(),
      () => respondStatus()
    );
    setTimeout(respondStatus, 700);
    return true;
  }
  if (request.type === "GET_UPDATE_STATUS" || request.type === "OPEN_UPDATE_LINK") {
    return processMessage(request, sendResponse);
  }

  executeWithHost(
    () => processMessage(request, sendResponse),
    (reason) => sendResponse({
      type: "error",
      error: reason?.code || "HOST_NOT_CONNECTED",
      message: reason?.message || "Host not connected.",
      host_version: reason?.hostVersion || null,
      min_required_host_version: reason?.minRequiredVersion || MIN_REQUIRED_HOST_VERSION,
      update_url: reason?.updateUrl || GITHUB_RELEASES_URL,
      update_command: reason?.updateCommand || null,
    })
  );
  return true;
});
