import pytest
from jsonschema import validate

# The contract strictly expected by host.py from the extension
extension_to_host_schema = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["ping", "open_folder", "prefetch", "download", "pause", "resume", "cancel"]},
        "url": {"type": "string"},
        "itag": {"type": "string"},
        "title": {"type": "string"},
        "videoId": {"type": "string"},
        "downloadId": {"type": "string"},
        "real_itag": {"type": ["string", "number"]},
        "save_location": {"type": "string"},
        "path": {"type": "string"}
    }
}

# The contract strictly expected by the extension from host.py
host_to_extension_schema = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["pong", "ok", "error", "progress", "done", "prefetch_result", "prefetch_error", "control_ack", "paused", "cancelled"]},
        "message": {"type": "string"},
        "action": {"type": "string", "enum": ["pause", "resume", "cancel"]},
        "ok": {"type": "boolean"},
        "reqUrl": {"type": "string"},
        "title": {"type": "string"},
        "videoId": {"type": "string"},
        "downloadId": {"type": "string"},
        "percent": {"type": "string"},
        "speed": {"type": "string"},
        "eta": {"type": "string"},
        "filename": {"type": "string"},
        "path": {"type": "string"},
        "size_mb": {"type": "number"},
        "qualities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "itag", "size_mb"]
            }
        }
    }
}

def test_extension_ping_schema():
    payload = {"type": "ping"}
    validate(instance=payload, schema=extension_to_host_schema)

def test_host_done_schema():
    payload = {
        "type": "done",
        "videoId": "123456",
        "filename": "video.mp4",
        "size_mb": 54.2,
        "path": "/home/user/Downloads/video.mp4"
    }
    validate(instance=payload, schema=host_to_extension_schema)

def test_extension_download_schema():
    payload = {
        "type": "download",
        "url": "https://youtube.com/watch?v=123",
        "title": "My Video",
        "videoId": "123",
        "itag": "video_1080",
        "save_location": "~/Downloads"
    }
    validate(instance=payload, schema=extension_to_host_schema)

def test_extension_pause_schema():
    payload = {
        "type": "pause",
        "downloadId": "dl_123"
    }
    validate(instance=payload, schema=extension_to_host_schema)

def test_host_control_ack_schema():
    payload = {
        "type": "control_ack",
        "action": "pause",
        "downloadId": "dl_123",
        "ok": True,
        "message": "Pause requested."
    }
    validate(instance=payload, schema=host_to_extension_schema)
