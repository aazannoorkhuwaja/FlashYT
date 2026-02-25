// Contract for all IPC and Extension string messages
const MSG = {
    HOST_PING: "ping",
    HOST_PONG: "pong",
    HOST_PREFETCH: "prefetch",
    HOST_PREFETCH_RESULT: "prefetch_result",
    HOST_DOWNLOAD: "download",
    HOST_PROGRESS: "progress",
    HOST_DONE: "done",
    HOST_ERROR: "error",
    HOST_OPEN_FOLDER: "open_folder",
    HOST_UPDATE_ENGINE: "update_engine",

    EXT_CHECK_STATUS: "CHECK_STATUS",
    EXT_PREFETCH: "PREFETCH",
    EXT_DOWNLOAD: "DOWNLOAD",
    EXT_OPEN_FOLDER: "OPEN_FOLDER",
    EXT_GET_HISTORY: "GET_HISTORY",
    EXT_GET_QUEUE: "GET_QUEUE",
    EXT_UPDATE_ENGINE: "UPDATE_ENGINE",

    ERR_NOT_CONNECTED: "HOST_NOT_CONNECTED",
    ERR_HOST_OUTDATED: "HOST_OUTDATED"
};

// Must match "version" field in host.py pong response.
// Bump this whenever the IPC protocol changes (new fields, renamed keys, etc.)
const EXPECTED_HOST_VERSION = "1.0.0";
