#!/bin/bash
echo "======================================"
echo " macOS / Linux Setup - Native Host"
echo "======================================"

# 1. Create a Python Virtual Environment
echo "[+] Creating Python virtual environment..."
python3 -m venv venv

# 2. Activate and Install Requirements
echo "[+] Installing yt-dlp dependency..."
source venv/bin/activate
pip install --upgrade pip
pip install yt-dlp

# 3. Run Native Host Installer
echo ""
echo "[+] Launching Native Messaging Registrar..."
python3 install_host.py
