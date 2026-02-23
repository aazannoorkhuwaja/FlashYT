@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  One-Click YouTube Downloader - Windows Setup
REM  Run this ONCE. After that, just paste the userscript!
REM ============================================================

echo.
echo  ======================================================
echo    One-Click YouTube Downloader - Setup (Windows)
echo    by Aazan Noor Khuwaja
echo  ======================================================
echo.

REM Get the directory where this script lives
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_DIR=%SCRIPT_DIR%\venv"

REM ---- Step 1: Check for Python ----
echo [1/5] Checking for Python...

python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo    ERROR: Python is NOT installed!
        echo.
        echo    Please install Python from:
        echo    https://www.python.org/downloads/
        echo.
        echo    IMPORTANT: During installation, check the box that says
        echo    "Add Python to PATH" at the very bottom of the installer!
        echo.
        echo    After installing Python, run this setup.bat again.
        echo.
        pause
        exit /b 1
    )
)

REM Find the correct python command
set "PYTHON_CMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=python3"
)
echo    [OK] Python found: 
%PYTHON_CMD% --version

REM ---- Step 2: Create virtual environment ----
echo [2/5] Setting up Python environment...

if not exist "%VENV_DIR%\Scripts\python.exe" (
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo    ERROR: Failed to create virtual environment.
        echo    Try: %PYTHON_CMD% -m pip install virtualenv
        pause
        exit /b 1
    )
    echo    [OK] Virtual environment created
) else (
    echo    [OK] Virtual environment already exists
)

REM ---- Step 3: Install Python packages ----
echo [3/5] Installing Python packages...

"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet --upgrade pip 2>nul
"%VENV_DIR%\Scripts\python.exe" -m pip install --quiet -U --pre "yt-dlp[default]" flask flask-cors 2>nul
echo    [OK] All Python packages installed

REM ---- Step 4: Check for FFmpeg ----
echo [4/5] Checking for FFmpeg...

where ffmpeg >nul 2>&1
if errorlevel 1 (
    if exist "%SCRIPT_DIR%\ffmpeg.exe" (
        echo    [OK] FFmpeg found in project folder
    ) else (
        echo    FFmpeg not found. Downloading...
        echo    (This may take a minute - it's a 90MB download^)
        echo.
        
        REM Try curl first (built into Windows 10+)
        curl -L -o "%SCRIPT_DIR%\ffmpeg.zip" "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" 2>nul
        
        if not exist "%SCRIPT_DIR%\ffmpeg.zip" (
            echo.
            echo    ERROR: Could not download FFmpeg automatically.
            echo.
            echo    Please download FFmpeg manually:
            echo    1. Go to: https://www.gyan.dev/ffmpeg/builds/
            echo    2. Download "ffmpeg-release-essentials.zip"
            echo    3. Extract ffmpeg.exe from the bin folder
            echo    4. Put ffmpeg.exe in: %SCRIPT_DIR%
            echo    5. Run this setup.bat again
            echo.
            pause
            exit /b 1
        )
        
        REM Extract just ffmpeg.exe using PowerShell
        echo    Extracting ffmpeg.exe...
        powershell -Command "try { Add-Type -AssemblyName System.IO.Compression.FileSystem; $zip = [System.IO.Compression.ZipFile]::OpenRead('%SCRIPT_DIR%\ffmpeg.zip'); foreach ($entry in $zip.Entries) { if ($entry.Name -eq 'ffmpeg.exe') { [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, '%SCRIPT_DIR%\ffmpeg.exe', $true); break } }; $zip.Dispose() } catch { Write-Host 'Extraction failed' }" 2>nul
        
        del "%SCRIPT_DIR%\ffmpeg.zip" 2>nul
        
        if exist "%SCRIPT_DIR%\ffmpeg.exe" (
            echo    [OK] FFmpeg downloaded successfully
        ) else (
            echo.
            echo    ERROR: Could not extract FFmpeg.
            echo    Please download ffmpeg.exe manually and put it in:
            echo    %SCRIPT_DIR%
            echo.
            pause
            exit /b 1
        )
    )
) else (
    echo    [OK] FFmpeg is installed system-wide
)

REM ---- Step 5: Start the server ----
echo [5/5] Starting the server...

REM Kill any existing server on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

REM Start the server with a VISIBLE window first to catch errors
start "YouTube Downloader Server" /min "%VENV_DIR%\Scripts\python.exe" "%SCRIPT_DIR%\server.py"

REM Wait for server to start
echo    Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Test if server is responding
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:5000/config >"%TEMP%\ytdl_check.txt" 2>nul
set /p HTTP_CODE=<"%TEMP%\ytdl_check.txt"
del "%TEMP%\ytdl_check.txt" 2>nul

if "%HTTP_CODE%"=="200" (
    echo    [OK] Server is running on http://127.0.0.1:5000
) else (
    echo.
    echo    WARNING: Server may not have started correctly.
    echo    Check the minimized "YouTube Downloader Server" window for errors.
    echo    Common fixes:
    echo      - Make sure port 5000 is not used by another program
    echo      - Try running: "%VENV_DIR%\Scripts\python.exe" "%SCRIPT_DIR%\server.py"
    echo.
)

REM ---- Create auto-start on boot ----
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_DIR%\YouTubeDownloader.vbs"

if not exist "%VBS_FILE%" (
    echo Set WshShell = CreateObject^("WScript.Shell"^)> "%VBS_FILE%"
    echo WshShell.Run """" ^& "%VENV_DIR%\Scripts\pythonw.exe" ^& """ """ ^& "%SCRIPT_DIR%\server.py" ^& """", 0, False>> "%VBS_FILE%"
    echo    [OK] Auto-start on boot configured
) else (
    echo    [OK] Auto-start already configured
)

REM ---- Done! ----
echo.
echo  ======================================================
echo    Setup Complete!
echo  ======================================================
echo.
echo  NEXT STEPS:
echo.
echo  1. Install Tampermonkey in your browser:
echo     https://www.tampermonkey.net/
echo.
echo  2. Click Tampermonkey icon ^> "Create a new script"
echo     Delete everything, paste the contents of:
echo     %SCRIPT_DIR%\userscript.js
echo     Then press Ctrl+S to save
echo.
echo  3. Go to YouTube, play any video, click Download!
echo.
echo  NOTE: The server is running in a minimized window.
echo  Do NOT close it! It will auto-start on next boot.
echo.
pause
