#!/usr/bin/env bash
set -euo pipefail

# Detect if running non-interactively (piped from curl)
INTERACTIVE=true
if [ ! -t 0 ]; then
  INTERACTIVE=false
  echo ""
  echo "⚠️  FlashYT detected it is running non-interactively (curl pipe mode)."
  echo ""
  echo "   This mode cannot prompt you for your Extension ID."
  echo "   Please run install.sh directly instead:"
  echo ""
  echo "   curl -L -o install.sh https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.sh"
  echo "   chmod +x install.sh"
  echo "   bash install.sh"
  echo ""
  echo "   This will allow the installer to ask for your Extension ID properly."
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
        echo "              or: sudo dnf install python3  (Fedora/RHEL)"
    fi
    exit 1
fi

# Check for Python 3.8+ specifically
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
    echo "[X] Python 3.8 or higher is required."
    python3 --version
    exit 1
fi

# 3) ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[X] ffmpeg is required but could not be found."
    if [[ $IS_MAC -eq 1 ]]; then
        echo "    Install via: brew install ffmpeg"
    else
        echo "    Install via: sudo apt install ffmpeg    (Ubuntu/Debian)"
        echo "              or: sudo dnf install ffmpeg    (Fedora/RHEL)"
    fi
    exit 1
fi

# 4a) Linux: install libsecret system library (needed by secretstorage / keyring)
if [[ $IS_MAC -eq 0 ]]; then
    echo ""
    echo "[*] Checking for libsecret system library..."
    HAS_LIBSECRET=0
    if python3 -c "import secretstorage" 2>/dev/null; then
        HAS_LIBSECRET=1
    elif python3 -c "import ctypes; ctypes.CDLL('libsecret-1.so.0')" 2>/dev/null; then
        HAS_LIBSECRET=1
    fi

    if [[ $HAS_LIBSECRET -eq 0 ]]; then
        echo "[*] libsecret not found. Attempting to install system package..."
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get install -y -q libsecret-1-dev >/dev/null 2>&1 || true
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y -q libsecret-devel >/dev/null 2>&1 || true
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -S --noconfirm --quiet libsecret >/dev/null 2>&1 || true
        else
            echo "[!] Could not auto-install libsecret (unsupported package manager)."
            echo "    Cookie-based downloads may not work. Install libsecret-1-dev manually if needed."
        fi
    else
        echo "[✓] libsecret available."
    fi
fi

# 4b) Python dependencies
echo ""
echo "[*] Installing Python dependencies (yt-dlp, pystray, Pillow, secretstorage)..."

_DEPS="yt-dlp pystray Pillow"
[[ $IS_MAC -eq 0 ]] && _DEPS="$_DEPS secretstorage"   # Linux-only

_pip_install() {
    python3 -m pip install $_DEPS "$@" --quiet 2>&1
}

if _pip_install 2>/dev/null; then
    echo "[✓] Dependencies installed."
elif _pip_install --break-system-packages 2>/dev/null; then
    echo "[✓] Dependencies installed (system pip with break-system-packages)."
elif _pip_install --user 2>/dev/null; then
    echo "[✓] Dependencies installed (--user mode)."
else
    echo "[X] Dependency installation failed."
    echo "    Tip: create and activate a Python venv, then re-run this installer:"
    echo "         python3 -m venv ~/.flashyt-venv"
    echo "         source ~/.flashyt-venv/bin/activate"
    echo "         bash install.sh"
    exit 1
fi

# 5) Install host files
DEST_DIR="$HOME/.local/share/YouTubeNativeDownloader"
echo ""
echo "[*] Installing native host to $DEST_DIR..."
mkdir -p "$DEST_DIR"
cp -r "$WORKDIR/host/"* "$DEST_DIR/"
cp "$WORKDIR/scripts/detect_extension_id.py" "$DEST_DIR/detect_extension_id.py"
cp "$WORKDIR/scripts/install_config.py" "$DEST_DIR/install_config.py"

cat > "$DEST_DIR/host.sh" <<'EOF'
#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(command -v python3)" "$DIR/host.py" "$@"
EOF
chmod +x "$DEST_DIR/host.sh"

# 6) Detect extension IDs (with interactive fallback)
echo ""
echo "[*] Attempting to auto-detect FlashYT extension IDs..."
EXT_IDS_CSV="$(python3 "$WORKDIR/scripts/detect_extension_id.py" --all-csv 2>/dev/null || true)"

if [[ -z "${EXT_IDS_CSV:-}" ]]; then
    echo ""
    echo "  [!] Auto-detection failed. The FlashYT extension may not be loaded yet,"
    echo "  or your browser stores profile data in a non-standard location."
    echo ""
    echo "  ► To find your extension ID manually:"
    echo "      1. Open chrome://extensions (or brave://extensions)"
    echo "      2. Enable 'Developer mode'"
    echo "      3. Find 'FlashYT' and copy the 32-character ID shown below the name"
    echo ""
    # Prompt for manual input (only when running interactively)
    if [[ -t 0 ]]; then
        while true; do
            echo ""
            echo "Paste your FlashYT Extension ID (32 characters, letters only):"
            echo "(Find it at chrome://extensions under the FlashYT card)"
            read -r EXTENSION_ID
            
            # Strip any whitespace the user may have accidentally included
            EXTENSION_ID=$(echo "$EXTENSION_ID" | tr -d '[:space:]')
            
            # Validate: must be exactly 32 lowercase alphabetic characters
            if echo "$EXTENSION_ID" | grep -qE '^[a-z]{32}$'; then
                echo "✓ Extension ID accepted: $EXTENSION_ID"
                EXT_IDS_CSV="$EXTENSION_ID"
                break
            else
                echo ""
                echo "❌ That doesn't look right. Extension IDs are exactly 32 lowercase letters."
                echo "   Example: abcdefghijklmnopabcdefghijklmnop"
                echo "   Please try again."
            fi
        done
    else
        echo "  [X] Running non-interactively. Load the extension first, then re-run: bash install.sh"
        exit 1
    fi
fi

# Always use the fixed extension ID instead of auto-discovered ones since we have a defined RSA keypair now.
FIXED_EXT_ID="epfpikjgfkpagepdhbancgmeganikbgo"
echo "[✓] Using fixed production Extension ID: $FIXED_EXT_ID"

# 7) Generate manifest
TEMPLATE="$DEST_DIR/manifests/com.youtube.native.ext.json"
TARGET_MANIFEST="$DEST_DIR/manifest_generated.json"
if [[ ! -f "$TEMPLATE" ]]; then
    echo "[X] Native host manifest template missing at $TEMPLATE"
    exit 1
fi

python3 - <<PY
import json
from pathlib import Path
template = Path(r"$TEMPLATE")
target = Path(r"$TARGET_MANIFEST")
host_sh = Path(r"$DEST_DIR") / "host.sh"
# Use the fixed ID
ext_ids = ["$FIXED_EXT_ID"]
data = json.loads(template.read_text(encoding="utf-8"))
data["path"] = str(host_sh)
data["allowed_origins"] = [f"chrome-extension://{ext_id}/" for ext_id in ext_ids]
target.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"[✓] Manifest written for Extension ID: $FIXED_EXT_ID")
PY

# 8) Register for browsers
echo ""
echo "[*] Registering native messaging host..."

_register_browser() {
    local dir="$1"
    if mkdir -p "$dir" 2>/dev/null; then
        cp "$TARGET_MANIFEST" "$dir/com.youtube.native.ext.json"
        echo "    [✓] $(basename "$(dirname "$dir")")"
    else
        echo "    [!] Could not write to $dir (skipped)"
    fi
}

if [[ $IS_MAC -eq 1 ]]; then
    _register_browser "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
    _register_browser "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
else
    _register_browser "$HOME/.config/google-chrome/NativeMessagingHosts"
    _register_browser "$HOME/.config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/.config/microsoft-edge/NativeMessagingHosts"
    # Snap-packaged browsers
    _register_browser "$HOME/snap/chromium/current/.config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/snap/brave/current/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    _register_browser "$HOME/snap/google-chrome/current/.config/google-chrome/NativeMessagingHosts"
fi

echo ""
echo "=================================================="
echo " ✓ SETUP COMPLETE"
echo "=================================================="
echo " Next steps:"
echo "  1) Reload the FlashYT extension:"
echo "     chrome://extensions  →  click the 🔄 refresh icon on FlashYT"
echo "  2) Open any YouTube video and click 'Download'."
echo ""
echo " Logs (if anything goes wrong):"
echo "     ~/.config/YouTubeNativeExt/host.log"
echo "=================================================="
