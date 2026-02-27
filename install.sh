#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " FlashYT - Mac/Linux Setup"
echo "=================================================="
echo ""

REPO_ARCHIVE_URL="https://codeload.github.com/aazannoorkhuwaja/youtube-native-ext/tar.gz/refs/heads/main"
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
    exit 1
fi

# 3) ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[X] ffmpeg is required but could not be found."
    exit 1
fi

# 4) Dependencies
echo ""
echo "[*] Installing Python dependencies (yt-dlp, pystray, Pillow, secretstorage)..."
python3 -m pip install yt-dlp pystray Pillow secretstorage --break-system-packages >/dev/null || {
    echo "[X] Dependency installation failed. Please re-run in an environment where pip installs are allowed."
    exit 1
}

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

# 6) Detect extension IDs
echo ""
echo "[*] Attempting to auto-detect FlashYT extension IDs..."
EXT_IDS_CSV="$(python3 "$WORKDIR/scripts/detect_extension_id.py" --all-csv 2>/dev/null || true)"

if [[ -z "${EXT_IDS_CSV:-}" ]]; then
    echo "[X] Could not auto-detect any FlashYT extension ID."
    echo "    Install/load the FlashYT extension first, then rerun this installer."
    exit 1
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
    echo "[X] Auto-detection returned no valid extension IDs."
    exit 1
fi

echo "[✓] Auto-detected ${#VALID_EXT_IDS[@]} extension ID(s)."

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
PY

# 8) Register for browsers
echo ""
echo "[*] Registering native messaging host..."
if [[ $IS_MAC -eq 1 ]]; then
    CHROME_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    BRAVE_DIR="$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    EDGE_DIR="$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
else
    CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
    CHROMIUM_DIR="$HOME/.config/chromium/NativeMessagingHosts"
    BRAVE_DIR="$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    EDGE_DIR="$HOME/.config/microsoft-edge/NativeMessagingHosts"
fi

mkdir -p "$CHROME_DIR" "$BRAVE_DIR" "$EDGE_DIR"
cp "$TARGET_MANIFEST" "$CHROME_DIR/com.youtube.native.ext.json"
cp "$TARGET_MANIFEST" "$BRAVE_DIR/com.youtube.native.ext.json"
cp "$TARGET_MANIFEST" "$EDGE_DIR/com.youtube.native.ext.json"

if [[ $IS_MAC -eq 0 ]]; then
    mkdir -p "$CHROMIUM_DIR"
    cp "$TARGET_MANIFEST" "$CHROMIUM_DIR/com.youtube.native.ext.json"
fi

echo "[✓] Native messaging registration complete."

echo ""
echo "=================================================="
echo " ✓ SETUP COMPLETE"
echo "=================================================="
echo " 1) Reload the FlashYT extension."
echo " 2) Open YouTube and start downloading."
echo " Logs: ~/.config/YouTubeNativeExt/host.log"
echo "=================================================="
