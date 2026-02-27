import os
import sys
import logging
import tempfile
from logging.handlers import RotatingFileHandler
import platform

def get_log_dir():
    if platform.system() == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.config')
        
    log_dir = os.path.join(base, 'YouTubeNativeExt')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logger():
    logger = logging.getLogger('FlashYT')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Primary path: user config directory.
    candidates = []
    try:
        candidates.append(os.path.join(get_log_dir(), 'host.log'))
    except Exception:
        pass

    # Fallback path: temp directory.
    candidates.append(os.path.join(tempfile.gettempdir(), 'flashyt-host.log'))

    for log_file in candidates:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=1, encoding='utf-8')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            return logger
        except Exception:
            continue

    # Last fallback: stderr to avoid import-time crashes.
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger

log = setup_logger()
