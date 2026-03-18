# FlashYT Windows 1-Click Installer
# Run this in PowerShell: irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$ReleaseUrl = "https://github.com/aazannoorkhuwaja/FlashYT/releases/latest/download/FlashYT-setup.exe"
$TempPath = Join-Path $env:TEMP "FlashYT-setup.exe"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  FlashYT - Windows 1-Click Setup" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Downloading FlashYT-setup.exe..." -NoNewline
Try {
    Invoke-WebRequest -Uri $ReleaseUrl -OutFile $TempPath -UserAgent "Mozilla/5.0"
    Write-Host " [Done]" -ForegroundColor Green
} Catch {
    Write-Host " [Failed]" -ForegroundColor Red
    Write-Error "Could not download the installer. Please check your internet connection."
}

Write-Host "[*] Launching installer..."
Start-Process -FilePath $TempPath -Wait

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " ✓ FlashYT Host Setup Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Next steps:"
Write-Host "  1) Load the 'extension' folder in chrome://extensions"
Write-Host "  2) Refresh YouTube and enjoy!"
Write-Host ""
Write-Host " Cleaning up..."
Remove-Item $TempPath -ErrorAction SilentlyContinue
