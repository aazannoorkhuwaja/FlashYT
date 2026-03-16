#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED_EXT_ID="epfpikjgfkpagepdhbancgmeganikbgo"
VALID_EXT_IDS=("$FIXED_EXT_ID")

cat > "$DIR/host.sh" <<'EOF'
#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(command -v python3)" "$DIR/host.py" "$@"
EOF
chmod +x "$DIR/host.sh"

TEMPLATE="$DIR/manifests/com.youtube.native.ext.json"
if [[ ! -f "$TEMPLATE" ]]; then
  echo "Manifest template missing at $TEMPLATE"
  exit 1
fi

generate_manifest() {
  local out="$1"
  python3 - <<PY
import json
from pathlib import Path
template = Path(r"$TEMPLATE")
target = Path(r"$out")
host_sh = Path(r"$DIR") / "host.sh"
ext_ids = ["$FIXED_EXT_ID"]
manifest = json.loads(template.read_text(encoding="utf-8"))
manifest["path"] = str(host_sh)
manifest["allowed_origins"] = [f"chrome-extension://{ext_id}/" for ext_id in ext_ids]
target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY
}

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  TARGETS=(
    "$HOME/.config/google-chrome/NativeMessagingHosts"
    "$HOME/.config/chromium/NativeMessagingHosts"
    "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    "$HOME/.config/microsoft-edge/NativeMessagingHosts"
  )
elif [[ "$OSTYPE" == "darwin"* ]]; then
  TARGETS=(
    "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    "$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"
  )
else
  echo "Unsupported OS for this setup script."
  exit 1
fi

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  generate_manifest "$target/com.youtube.native.ext.json"
done

echo "Native messaging host installed successfully for ${#VALID_EXT_IDS[@]} extension ID(s)."
