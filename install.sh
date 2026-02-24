#!/usr/bin/env bash
set -e

echo "=================================================="
echo " YouTube Native Downloader - Mac/Linux Setup"
echo "=================================================="
echo ""

# 1. Detect OS
OS_NAME=$(uname -s)
if [[ "$OS_NAME" == "Darwin" ]]; then
    echo "[!] Detected macOS"
    IS_MAC=1
elif [[ "$OS_NAME" == "Linux" ]]; then
    echo "[!] Detected Linux"
    IS_MAC=0
else
    echo "[X] Unsupported OS: $OS_NAME"
    exit 1
fi

# 2. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[X] Python 3 is required but could not be found."
    if [[ $IS_MAC -eq 1 ]]; then
        echo "    Install via Homebrew: brew install python3"
    else
        echo "    Install via apt: sudo apt install python3"
    fi
    exit 1
fi

# 3. Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "[X] ffmpeg is required but could not be found."
    if [[ $IS_MAC -eq 1 ]]; then
        echo "    Install via Homebrew: brew install ffmpeg"
    else
        echo "    Install via apt: sudo apt install ffmpeg"
    fi
    exit 1
fi

# 4. Install Python Dependencies
echo ""
echo "[*] Installing required Python libraries (yt-dlp, pystray, Pillow, secretstorage)..."
# Using --break-system-packages for convenience as requested by prompt constraints, 
# although a venv would be safer in modern Ubuntu.
python3 -m pip install yt-dlp pystray Pillow secretstorage --break-system-packages || {
    echo "[X] Failed to install Python dependencies. If your OS forbids this, you must run this script inside a venv."
    exit 1
}

# 5. Clone/Copy Host files
DEST_DIR="$HOME/.local/share/YouTubeNativeDownloader"
echo ""
echo "[*] Installing Native Host to $DEST_DIR..."
mkdir -p "$DEST_DIR"

# Assume script is run from the repo root
if [[ -d "host" ]]; then
    cp -r host/* "$DEST_DIR/"
else
    echo "[X] Could not find the 'host' directory. Please run this script from the root of the extracted repository."
    exit 1
fi

# 6. Extract Extension ID dynamically
echo ""
echo "[*] Attempting to auto-detect Chrome Extension ID..."
EXT_ID=$(python3 "scripts/detect_extension_id.py" 2>/dev/null || echo "")

if [[ -z "$EXT_ID" || ${#EXT_ID} -ne 32 ]]; then
    echo "[!] Could not auto-detect the Extension ID."
    echo "    1. Open Chrome/Brave and go to chrome://extensions"
    echo "    2. Enable Developer Mode"
    echo "    3. Load the unpacked 'extension' folder"
    echo "    4. Copy the 32-character ID the browser assigns it"
    echo ""
    read -p "Paste your Extension ID here: " EXT_ID
    
    # Strip whitespace
    EXT_ID=$(echo "$EXT_ID" | tr -d '[:space:]')
    
    if [[ ${#EXT_ID} -ne 32 ]]; then
        echo "[X] Invalid ID. Must be exactly 32 characters."
        exit 1
    fi
else
    echo "[✓] Auto-detected Extension ID: $EXT_ID"
fi

# 7. Write Manifest Files
MANIFEST_TEMPLATE="$DEST_DIR/com.youtube.native.ext.json"
HOST_PATH="$DEST_DIR/host.py"

# Make sure the host path points directly to our python runner script
cat "$MANIFEST_TEMPLATE" | \
    sed "s|\"path\": \".*\"|\"path\": \"$(which python3) $HOST_PATH\"|" | \
    sed "s|EXTENSION_ID_PLACEHOLDER|$EXT_ID|" > "$DEST_DIR/manifest_generated.json"

echo ""
echo "[*] Registering Native Messaging bindings..."

if [[ $IS_MAC -eq 1 ]]; then
    CHROME_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    BRAVE_DIR="$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
else
    CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
    # Fallback chromium
    CHROMIUM_DIR="$HOME/.config/chromium/NativeMessagingHosts"
    BRAVE_DIR="$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
fi

mkdir -p "$CHROME_DIR" "$BRAVE_DIR"
cp "$DEST_DIR/manifest_generated.json" "$CHROME_DIR/com.youtube.native.ext.json"
cp "$DEST_DIR/manifest_generated.json" "$BRAVE_DIR/com.youtube.native.ext.json"

if [[ $IS_MAC -eq 0 ]]; then
    mkdir -p "$CHROMIUM_DIR"
    cp "$DEST_DIR/manifest_generated.json" "$CHROMIUM_DIR/com.youtube.native.ext.json"
fi

echo "[✓] Registrations complete in user config."

# 8. Finished
echo ""
echo "=================================================="
echo " ✓ SETUP COMPLETE!"
echo "=================================================="
echo " 1. Make sure you have installed the browser extension."
echo " 2. Visit any YouTube video."
echo " 3. Click the red ⬇ Download button."
echo ""
echo " View logs at: ~/.config/YouTubeNativeExt/host.log"
echo "=================================================="
