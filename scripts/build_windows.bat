@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo YouTube Native Downloader - Windows Build Pipeline
echo ==================================================

cd /d "%~dp0\.."

echo.
echo [1/4] Checking Python Dependencies...
pip install -r host\requirements.txt pyinstaller
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install requirements.
    exit /b 1
)

echo.
echo [2/4] Building host.exe (Native Messaging Target)...
pyinstaller --clean --onefile --noconsole --name host --distpath host\dist --workpath host\build host\host.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile host.exe
    exit /b 1
)

echo.
echo [3/4] Building detect_ext.exe and register_host_windows.exe (Installer Utils)...
pyinstaller --clean --onefile --console --name detect_ext --distpath scripts\dist --workpath scripts\build scripts\detect_extension_id.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to compile detect_ext.exe
    exit /b 1
)

pyinstaller --clean --onefile --console --name register_host_windows --distpath scripts\dist --workpath scripts\build scripts\register_host_windows.py
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
echo Installer generated at: dist\youtube-native-downloader-setup.exe
echo ==================================================
pause
