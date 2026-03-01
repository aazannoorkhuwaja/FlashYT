#!/usr/bin/env bash
# FlashYT Uninstaller — removes native host, manifests, and state files.
# Run with: curl -fsSL https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/uninstall.sh | bash
set -euo pipefail

echo "=================================================="
echo " FlashYT - Uninstaller"
echo "=================================================="
echo ""

OS_NAME="$(uname -s)"
IS_MAC=0
[[ "$OS_NAME" == "Darwin" ]] && IS_MAC=1

# 1) Remove host installation directory
DEST_DIR="$HOME/.local/share/YouTubeNativeDownloader"
if [[ -d "$DEST_DIR" ]]; then
    rm -rf "$DEST_DIR"
    echo "[✓] Removed host files: $DEST_DIR"
else
    echo "[~] Host dir not found (already removed?): $DEST_DIR"
fi

# 2) Remove native messaging manifests from all browsers

_remove_manifest() {
    local dir="$1"
    local manifest="$dir/com.youtube.native.ext.json"
    if [[ -f "$manifest" ]]; then
        rm -f "$manifest"
        echo "[✓] Removed manifest from: $dir"
    fi
}

if [[ $IS_MAC -eq 1 ]]; then
    _remove_manifest "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    _remove_manifest "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _remove_manifest "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
    _remove_manifest "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
else
    _remove_manifest "$HOME/.config/google-chrome/NativeMessagingHosts"
    _remove_manifest "$HOME/.config/chromium/NativeMessagingHosts"
    _remove_manifest "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _remove_manifest "$HOME/.config/microsoft-edge/NativeMessagingHosts"
    _remove_manifest "$HOME/snap/chromium/current/.config/chromium/NativeMessagingHosts"
    _remove_manifest "$HOME/snap/brave/current/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
fi

# 3) Remove log and config files
LOG_DIR="$HOME/.config/YouTubeNativeExt"
if [[ -d "$LOG_DIR" ]]; then
    rm -rf "$LOG_DIR"
    echo "[✓] Removed log directory: $LOG_DIR"
fi

echo ""
echo "=================================================="
echo " ✓ FlashYT native host fully uninstalled."
echo "=================================================="
echo " To finish: go to chrome://extensions and"
echo " click 'Remove' on the FlashYT extension."
echo "=================================================="
