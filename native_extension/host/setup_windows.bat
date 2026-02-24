@echo off
echo ======================================
echo  Windows Setup - Native Host
echo ======================================

:: 1. Create a Python Virtual Environment
echo [+] Creating Python virtual environment...
python -m venv venv

:: 2. Activate and Install Requirements
echo [+] Installing yt-dlp dependency...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install yt-dlp

:: 3. Run Native Host Installer
echo.
echo [+] Launching Native Messaging Registrar...
python install_host.py

echo.
pause
