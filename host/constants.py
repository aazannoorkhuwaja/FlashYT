"""
constants.py - Shared constants for FlashYT host components.
"""

# Synchronized User-Agent for all HTTP requests to prevent 403 Forbidden errors.
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Public fallback InnerTube key (allows zero-config prefetch if FLASHYT_INNERTUBE_KEY is not set)
FALLBACK_INNERTUBE_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
