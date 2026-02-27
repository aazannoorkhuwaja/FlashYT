@echo off
setlocal

set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
set "MANIFEST_DIR=%APPDATA%\YouTubeNativeExt"
set "DETECT_SCRIPT=%DIR%\..\scripts\detect_extension_id.py"
set "EXT_IDS="

mkdir "%MANIFEST_DIR%" 2>nul

if not exist "%DETECT_SCRIPT%" (
  echo [X] Could not find extension auto-detection script.
  echo Run setup from the repository root using install.sh or the Windows installer package.
  exit /b 1
)

for /f "usebackq delims=" %%I in (`python "%DETECT_SCRIPT%" --all-csv 2^>nul`) do set "EXT_IDS=%%I"

if not defined EXT_IDS (
  echo [X] Could not auto-detect any FlashYT extension ID.
  echo Install or enable FlashYT first, then rerun setup.
  exit /b 1
)

echo @echo off > "%DIR%\host_runner.bat"
echo cd /d "%DIR%" >> "%DIR%\host_runner.bat"
echo python host.py %%* >> "%DIR%\host_runner.bat"

powershell -NoProfile -Command "$manifest = Get-Content '%DIR%\manifests\com.youtube.native.ext.win.json' -Raw | ConvertFrom-Json; $manifest.path = '%DIR%\host_runner.bat'; $ids = '%EXT_IDS%'.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_.Length -eq 32 }; $manifest.allowed_origins = @($ids | ForEach-Object { 'chrome-extension://' + $_ + '/' }); $manifest | ConvertTo-Json -Depth 8 | Set-Content '%MANIFEST_DIR%\com.youtube.native.ext.json' -Encoding Ascii"
if errorlevel 1 (
  echo [X] Failed to generate native host manifest.
  exit /b 1
)

reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.youtube.native.ext" /ve /t REG_SZ /d "%MANIFEST_DIR%\com.youtube.native.ext.json" /f >nul
reg add "HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.youtube.native.ext" /ve /t REG_SZ /d "%MANIFEST_DIR%\com.youtube.native.ext.json" /f >nul
reg add "HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.youtube.native.ext" /ve /t REG_SZ /d "%MANIFEST_DIR%\com.youtube.native.ext.json" /f >nul
reg add "HKCU\Software\Chromium\NativeMessagingHosts\com.youtube.native.ext" /ve /t REG_SZ /d "%MANIFEST_DIR%\com.youtube.native.ext.json" /f >nul

echo Native messaging host installed successfully with auto-detected extension IDs.
pause
