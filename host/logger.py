import os
import sys
import logging
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
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, 'host.log')
    logger = logging.getLogger('oneclick_ytmp4')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=1, encoding='utf-8')
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

log = setup_logger()
