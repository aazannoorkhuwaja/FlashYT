#!/usr/bin/env bash
set -euo pipefail

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

# 2) Python
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
cp "$WORKDIR/scripts/constants.py" "$DEST_DIR/constants.py"

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
        read -rp "  Paste the extension ID here (or press Enter to skip and re-run later): " MANUAL_ID
        MANUAL_ID="$(echo "${MANUAL_ID:-}" | tr -d '[:space:]')"
        if [[ ${#MANUAL_ID} -eq 32 ]]; then
            EXT_IDS_CSV="$MANUAL_ID"
            echo "  [✓] Using extension ID: $MANUAL_ID"
        else
            echo "  [X] Invalid or empty ID. Run the installer again after loading the extension."
            exit 1
        fi
    else
        echo "  [X] Running non-interactively. Load the extension first, then re-run: bash install.sh"
        exit 1
    fi
fi

IFS=',' read -r -a EXT_IDS <<< "$EXT_IDS_CSV"
VALID_EXT_IDS=()
for id in "${EXT_IDS[@]}"; do
    id="$(echo "$id" | tr -d '[:space:]')"
    if [[ ${#id} -eq 32 ]]; then
        VALID_EXT_IDS+=("$id")
    fi
done

if [[ ${#VALID_EXT_IDS[@]} -eq 0 ]]; then
    echo "[X] No valid 32-character extension ID found."
    exit 1
fi

echo "[✓] Using ${#VALID_EXT_IDS[@]} extension ID(s): ${VALID_EXT_IDS[*]}"

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
ext_ids = [i for i in "$EXT_IDS_CSV".split(",") if len(i.strip()) == 32]
data = json.loads(template.read_text(encoding="utf-8"))
data["path"] = str(host_sh)
data["allowed_origins"] = [f"chrome-extension://{ext_id}/" for ext_id in dict.fromkeys(i.strip() for i in ext_ids)]
target.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"[✓] Manifest written with {len(data['allowed_origins'])} allowed origin(s).")
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
    # Snap-packaged browsers store NativeMessagingHosts in a different location
    _register_browser "$HOME/snap/chromium/current/.config/chromium/NativeMessagingHosts"
    _register_browser "$HOME/snap/brave/current/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
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
