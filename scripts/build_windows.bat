@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo FlashYT - Windows Build Pipeline
echo ==================================================

cd /d "%~dp0\.."

:: ── Version (single source of truth) ─────────────────────────────────────────
set "VERSION=2.2.5"
echo Build version: %VERSION%

:: ── Preflight: vendor binaries must exist before Inno Setup can package them ──
if not exist "vendor\yt-dlp.exe" (
    echo [ERROR] vendor\yt-dlp.exe not found.
    echo Download from https://github.com/yt-dlp/yt-dlp/releases/latest
    exit /b 1
)
if not exist "vendor\ffmpeg.exe" (
    echo [ERROR] vendor\ffmpeg.exe not found.
    echo Download from https://github.com/BtbN/FFmpeg-Builds/releases
    exit /b 1
)

echo.
echo [1/4] Checking Python Dependencies...
pip install -r host\requirements.txt pyinstaller
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install requirements.
    exit /b 1
)

echo.
echo [2/4] Building host.exe (Native Messaging Target)...
:: --specpath host\build  prevents host.spec from landing in repo root
:: FLASHYT_HOST_VERSION is baked in so tray shows the correct version at runtime
set "FLASHYT_HOST_VERSION=%VERSION%"
pyinstaller --clean --onefile --noconsole --name host ^
    --noupx ^
    --paths host ^
    --distpath host\dist ^
    --workpath host\build ^
    --specpath host\build ^
    --hidden-import=pystray._win32 ^
    --hidden-import=pystray._base ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageDraw ^
    --hidden-import=PIL.ImageFont ^
    host\host.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile host.exe
    exit /b 1
)

echo.
echo [3/4] Building detect_ext.exe and register_host_windows.exe (Installer Utils)...
pyinstaller --clean --onefile --console --noupx --name detect_ext ^
    --paths scripts ^
    --distpath scripts\dist ^
    --workpath scripts\build ^
    --specpath scripts\build ^
    scripts\detect_extension_id.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile detect_ext.exe
    exit /b 1
)

pyinstaller --clean --onefile --console --noupx --name register_host_windows ^
    --distpath scripts\dist ^
    --workpath scripts\build ^
    --specpath scripts\build ^
    scripts\register_host_windows.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile register_host_windows.exe
    exit /b 1
)

echo.
echo [4/4] Compiling Windows Installer (Inno Setup)...
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\iscc.exe"
) else (
    echo [WARNING] Inno Setup 6 not found in standard paths. Skipping installer compilation.
    echo Make sure to run installer_windows.iss manually to generate the setup.exe.
    exit /b 0
)

%ISCC% installer_windows.iss
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b 1
)

echo.
echo ==================================================
echo COMPLETED SUCCESSFULLY!
echo Installer generated at: dist\FlashYT-setup.exe
echo ==================================================
if /I not "%CI%"=="true" pause
