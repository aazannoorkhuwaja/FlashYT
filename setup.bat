@echo off
REM ============================================================
REM  One-Click YouTube Downloader — Windows Setup
REM  Run this once and everything will just work!
REM ============================================================

echo.
echo  ======================================================
echo    One-Click YouTube Downloader — Auto Setup (Windows)
echo    by Aazan Noor Khuwaja
echo  ======================================================
echo.

REM Get the directory where this script lives (= project root)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM ---- Step 1: Check for Python ----
echo [1/5] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo    Python not found! Installing via winget...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo.
        echo    ERROR: Could not install Python automatically.
        echo    Please install Python 3.10+ from https://www.python.org/downloads/
        echo    IMPORTANT: Check "Add Python to PATH" during installation!
        echo.
        pause
        exit /b 1
    )
    echo    Installed Python. You may need to restart this script.
)
echo    [OK] Python is installed

REM ---- Step 2: Create virtual environment ----
echo [2/5] Setting up Python environment...
if not exist "%SCRIPT_DIR%\venv" (
    python -m venv "%SCRIPT_DIR%\venv"
    echo    [OK] Virtual environment created
) else (
    echo    [OK] Virtual environment already exists
)

REM ---- Step 3: Install Python packages ----
echo [3/5] Installing Python packages...
"%SCRIPT_DIR%\venv\Scripts\pip.exe" install --quiet --upgrade pip >nul 2>&1
"%SCRIPT_DIR%\venv\Scripts\pip.exe" install --quiet yt-dlp flask flask-cors >nul 2>&1
echo    [OK] All Python packages installed

REM ---- Step 4: Check for FFmpeg ----
echo [4/5] Checking for FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo    FFmpeg not found. Downloading portable FFmpeg...
    if not exist "%SCRIPT_DIR%\ffmpeg.exe" (
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile '%SCRIPT_DIR%\ffmpeg.zip'" >nul 2>&1
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\ffmpeg.zip' -DestinationPath '%SCRIPT_DIR%\ffmpeg_temp' -Force" >nul 2>&1
        copy "%SCRIPT_DIR%\ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" "%SCRIPT_DIR%\ffmpeg.exe" >nul 2>&1
        rmdir /s /q "%SCRIPT_DIR%\ffmpeg_temp" >nul 2>&1
        del "%SCRIPT_DIR%\ffmpeg.zip" >nul 2>&1
    )
    echo    [OK] FFmpeg downloaded to project folder
) else (
    echo    [OK] FFmpeg is installed system-wide
)

REM ---- Step 5: Create auto-start shortcut ----
echo [5/5] Setting up auto-start on boot...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_DIR%\YouTubeDownloader.vbs"

REM Create a VBS script that starts the server silently (no terminal window)
(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run Chr^(34^) ^& "%SCRIPT_DIR%\venv\Scripts\pythonw.exe" ^& Chr^(34^) ^& " " ^& Chr^(34^) ^& "%SCRIPT_DIR%\server.py" ^& Chr^(34^), 0, False
) > "%SHORTCUT%"
echo    [OK] Server will auto-start silently on every boot

REM ---- Start the server now ----
echo.
echo  Starting the server...
start "" /b "%SCRIPT_DIR%\venv\Scripts\pythonw.exe" "%SCRIPT_DIR%\server.py"

REM Wait a moment and verify
timeout /t 3 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/config' -UseBasicParsing -TimeoutSec 5; if ($r.StatusCode -eq 200) { Write-Host '   [OK] Server is running on http://127.0.0.1:5000' } } catch { Write-Host '   [!] Server started but not responding yet (give it a few seconds)' }" 2>nul

echo.
echo  ======================================================
echo    Setup Complete!
echo  ======================================================
echo.
echo  What to do next:
echo.
echo  1. Install Tampermonkey in your browser
echo     https://www.tampermonkey.net/
echo.
echo  2. Open Tampermonkey, Create a new script
echo     Copy-paste the contents of userscript.js and save
echo.
echo  3. Go to YouTube, play any video, and click the
echo     red Download button!
echo.
pause
