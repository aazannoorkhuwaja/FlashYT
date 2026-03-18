#!/usr/bin/env bash
# FlashYT Installer — installs native host, manifests, and dependencies.
set -euo pipefail

# Detect if running non-interactively (piped from curl)
if [ ! -t 0 ]; then
  echo ""
  echo "⚠️  FlashYT detected it is running non-interactively (curl pipe mode)."
  echo ""
  echo "   Please download and run install.sh directly instead:"
  echo ""
  echo "   curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh"
  echo "   chmod +x install.sh"
  echo "   bash install.sh"
  echo ""
  exit 1
fi

echo "=================================================="
echo " FlashYT - Mac/Linux Setup"
echo "=================================================="
echo ""

REPO_ARCHIVE_URL="https://codeload.github.com/aazannoorkhuwaja/FlashYT/tar.gz/refs/heads/main"
WORKDIR=""

if [[ -d "./host" && -d "./scripts" ]]; then
    WORKDIR="$(pwd)"
else
    echo "[*] Downloading setup assets..."
    TMP_SRC="$(mktemp -d)"
    curl -fsSL "$REPO_ARCHIVE_URL" | tar -xz -C "$TMP_SRC" --strip-components=1
    WORKDIR="$TMP_SRC"
fi

# 1) Detect OS
OS_NAME="$(uname -s)"
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

# 2) Python & Version Check
if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] Python 3 is required but could not be found."
    if [[ $IS_MAC -eq 1 ]]; then
        echo "    Install via: brew install python3"
    else
        echo "    Install via: sudo apt install python3  (Ubuntu/Debian)"
    fi
    exit 1
fi

# Check for Python 3.8+ specifically
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" || {
    echo "[X] Python 3.8 or higher is required."
    echo "    Your version: $(python3 --version)"
    echo "    Upgrade via: sudo apt install python3.10  (Ubuntu)"
    echo "              or: brew install python3         (macOS)"
    exit 1
}

# 3) ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[X] ffmpeg is required but could not be found."
    if [[ $IS_MAC -eq 1 ]]; then
        echo "    Install via: brew install ffmpeg"
    else
        echo "    Install via: sudo apt install ffmpeg    (Ubuntu/Debian)"
    fi
    exit 1
fi

# 4) Dependencies
echo ""
echo "[*] Installing dependencies..."
_DEPS=("yt-dlp" "pystray" "Pillow")
[[ $IS_MAC -eq 0 ]] && _DEPS+=("secretstorage")

_pip_install() {
    python3 -m pip install "${_DEPS[@]}" "$@" --quiet 2>&1
}

if _pip_install 2>/dev/null || _pip_install --break-system-packages 2>/dev/null || _pip_install --user 2>/dev/null; then
    echo "[✓] Dependencies installed."
else
    echo "[X] Dependency installation failed."
    exit 1
fi

# 5) Install host files
DEST_DIR="$HOME/.local/share/YouTubeNativeDownloader"
mkdir -p "$DEST_DIR"
cp -r "$WORKDIR/host/"* "$DEST_DIR/"
cp "$WORKDIR/scripts/detect_extension_id.py" "$DEST_DIR/detect_extension_id.py"
cp "$WORKDIR/scripts/install_config.py" "$DEST_DIR/install_config.py"

cat > "$DEST_DIR/host.sh" <<EOF
#!/usr/bin/env bash
exec "\$(command -v python3)" "$DEST_DIR/host.py" "\$@"
EOF
chmod +x "$DEST_DIR/host.sh"

# 6) Fixed Production Extension ID
FIXED_EXT_ID="epfpikjgfkpagepdhbancgmeganikbgo"
echo "[✓] Using production Extension ID: $FIXED_EXT_ID"

# 7) Generate manifest
TEMPLATE="$DEST_DIR/manifests/com.youtube.native.ext.json"
TARGET_MANIFEST="$DEST_DIR/com.youtube.native.ext.json"

python3 - <<PY
import json
from pathlib import Path
template = Path(r"$TEMPLATE")
target = Path(r"$TARGET_MANIFEST")
host_sh = Path(r"$DEST_DIR/host.sh")
ext_ids = ["$FIXED_EXT_ID"]
data = json.loads(template.read_text(encoding="utf-8"))
data["path"] = str(host_sh)
data["allowed_origins"] = [f"chrome-extension://{ext_id}/" for ext_id in ext_ids]
target.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY

# 8) Register for browsers
_register_browser() {
    local dir="$1"
    if mkdir -p "$dir" 2>/dev/null; then
        cp "$TARGET_MANIFEST" "$dir/com.youtube.native.ext.json"
        echo "    [✓] Registered for: $(basename "$(dirname "$dir")")"
    fi
}

if [[ $IS_MAC -eq 1 ]]; then
    _register_browser "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
else
    # Standard .deb / manual installs
    _register_browser "$HOME/.config/google-chrome/NativeMessagingHosts"
    _register_browser "$HOME/.config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/.config/microsoft-edge/NativeMessagingHosts"
    
    # Snap installs
    _register_browser "$HOME/snap/chromium/current/.config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/snap/brave/current/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/snap/google-chrome/current/.config/google-chrome/NativeMessagingHosts"

    # Flatpak installs
    _register_browser "$HOME/.var/app/com.google.Chrome/config/google-chrome/NativeMessagingHosts"
    _register_browser "$HOME/.var/app/org.chromium.Chromium/config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/.var/app/com.microsoft.Edge/config/microsoft-edge/NativeMessagingHosts"
fi

echo ""
echo "=================================================="
echo " ✓ FlashYT Setup Complete!"
echo "=================================================="
echo " Next steps:"
echo "  1) Refresh your YouTube tab."
echo "  2) Click the Download button!"
echo ""
echo " Logs (if needed):"
echo "  ~/.config/YouTubeNativeExt/host.log"
echo "=================================================="
