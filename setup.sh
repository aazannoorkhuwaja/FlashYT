#!/bin/bash
# ============================================================
#  One-Click YouTube Downloader — Setup Script
#  Run this once after cloning and everything will just work!
# ============================================================

set -e  # Stop on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║${NC}  ${BOLD}One-Click YouTube Downloader — Auto Setup${NC}       ${RED}║${NC}"
echo -e "${RED}║${NC}  ${BLUE}by Aazan Noor Khuwaja${NC}                           ${RED}║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script lives (= project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
SERVICE_NAME="yt-downloader"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

# ---- Step 0: Auto-Update (Pull latest fixes from GitHub) ----
echo -e "${YELLOW}[0/5]${NC} Checking for updates from GitHub..."
cd "$SCRIPT_DIR"
if git rev-parse --is-inside-work-tree &>/dev/null; then
    # Stash any accidental local changes so pull doesn't fail
    git stash -q || true
    git pull origin main --quiet || true
    echo -e "   ${GREEN}✓ Updated to latest version${NC}"
else
    echo -e "   ${BLUE}ℹ Not a git repository, skipping auto-update${NC}"
fi
echo ""

# ---- Step 1: Check system dependencies ----
echo -e "${YELLOW}[1/5]${NC} Checking system dependencies..."

MISSING_DEPS=()

if ! command -v python3 &>/dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
    MISSING_DEPS+=("python3-pip")
fi

if ! python3 -c "import venv" &>/dev/null 2>&1; then
    MISSING_DEPS+=("python3-venv")
fi

if ! python3 -c "import tkinter" &>/dev/null 2>&1; then
    MISSING_DEPS+=("python3-tk")
fi

if ! command -v ffmpeg &>/dev/null; then
    MISSING_DEPS+=("ffmpeg")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}   Installing missing packages: ${MISSING_DEPS[*]}${NC}"
    echo -e "   ${BLUE}(You may be asked for your password)${NC}"
    if command -v apt &>/dev/null; then
        sudo apt update -qq
        sudo apt install -y -qq "${MISSING_DEPS[@]}"
    elif command -v dnf &>/dev/null; then
        # Map Debian/Ubuntu package names to Fedora package names
        FEDORA_DEPS=()
        for dep in "${MISSING_DEPS[@]}"; do
            if [ "$dep" = "python3-venv" ]; then
                continue # Included in python3 on Fedora
            elif [ "$dep" = "python3-tk" ]; then
                FEDORA_DEPS+=("python3-tkinter")
            else
                FEDORA_DEPS+=("$dep")
            fi
        done
        if [ ${#FEDORA_DEPS[@]} -gt 0 ]; then
            sudo dnf install -y "${FEDORA_DEPS[@]}"
        fi
    else
        echo -e "${RED}   Unsupported package manager. Please install manually:${NC} ${MISSING_DEPS[*]}"
        exit 1
    fi
    echo -e "   ${GREEN}✓ System dependencies installed${NC}"
else
    echo -e "   ${GREEN}✓ All system dependencies already installed${NC}"
fi

# ---- Step 2: Create Python virtual environment ----
echo -e "${YELLOW}[2/5]${NC} Setting up Python environment..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "   ${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "   ${GREEN}✓ Virtual environment already exists${NC}"
fi

# ---- Step 3: Install Python packages ----
echo -e "${YELLOW}[3/5]${NC} Installing Python packages..."

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet yt-dlp flask flask-cors secretstorage
echo -e "   ${GREEN}✓ All Python packages installed${NC}"

# ---- Step 4: Create systemd service for auto-start ----
echo -e "${YELLOW}[4/5]${NC} Setting up auto-start service..."

mkdir -p "$HOME/.config/systemd/user"

cat > "$SERVICE_FILE" << SERVICEEOF
[Unit]
Description=YouTube Video Downloader Flask Server
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
# Silently auto-update the code on every boot/restart (ignores errors if offline)
ExecStartPre=-/usr/bin/git -C "$SCRIPT_DIR" pull origin main --quiet
# Silently auto-upgrade yt-dlp on every boot/restart to fix YouTube changes
ExecStartPre=-"$VENV_DIR/bin/pip" install --quiet --upgrade yt-dlp
ExecStart=/bin/bash -c '"$VENV_DIR/bin/python" "$SCRIPT_DIR/server.py"'
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SERVICEEOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME" --quiet
systemctl --user restart "$SERVICE_NAME"

# Enable lingering so service starts on boot (even before login screen)
loginctl enable-linger "$(whoami)" 2>/dev/null || true

echo -e "   ${GREEN}✓ Server will now auto-start on every boot${NC}"

# ---- Step 5: Verify ----
echo -e "${YELLOW}[5/5]${NC} Verifying everything works..."

sleep 5

if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    echo -e "   ${GREEN}✓ Server is running!${NC}"
else
    echo -e "   ${RED}✗ Server failed to start. Run this to see the error:${NC}"
    echo -e "     systemctl --user status $SERVICE_NAME"
    exit 1
fi

# Test HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/config 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "   ${GREEN}✓ Server responding on http://127.0.0.1:5000${NC}"
else
    echo -e "   ${YELLOW}⚠ Server started but not responding yet (give it a few seconds)${NC}"
fi

# ---- Done! ----
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}✅ Setup Complete!${NC}                              ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}What to do next:${NC}"
echo ""
echo -e "  1. Install ${BLUE}Tampermonkey${NC} in your browser"
echo -e "     → https://www.tampermonkey.net/"
echo ""
echo -e "  2. Open Tampermonkey → ${BLUE}Create a new script${NC}"
echo -e "     Copy-paste the contents of ${BOLD}userscript.js${NC} and save"
echo ""
echo -e "  3. Go to YouTube, play any video, and click the"
echo -e "     red ${RED}${BOLD}Download${NC} button! 🎉"
echo ""
echo -e "  ${BLUE}Useful commands:${NC}"
echo -e "    Check status  →  systemctl --user status $SERVICE_NAME"
echo -e "    View logs     →  journalctl --user -u $SERVICE_NAME -f"
echo -e "    Restart       →  systemctl --user restart $SERVICE_NAME"
echo ""

