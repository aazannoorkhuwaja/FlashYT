# FlashYT Windows Auto-Updater
# Run with: irm https://raw.githubusercontent.com/aazannoorkhuwaja/FlashYT/main/scripts/update_windows.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=================================================="
Write-Host "  FlashYT - Windows Update"
Write-Host "=================================================="
Write-Host ""

$DEST = "$env:LOCALAPPDATA\YouTubeNativeDownloader"
$REPO_URL = "https://codeload.github.com/aazannoorkhuwaja/FlashYT/tar.gz/refs/heads/main"
$TMP = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "flashyt_update_$([System.IO.Path]::GetRandomFileName())")

try {
    Write-Host "[*] Downloading latest FlashYT..."
    New-Item -ItemType Directory -Path $TMP -Force | Out-Null
    $archive = Join-Path $TMP "flashyt.tar.gz"
    Invoke-WebRequest -Uri $REPO_URL -OutFile $archive -UseBasicParsing
    tar -xzf $archive -C $TMP --strip-components=1
    Write-Host "[OK] Download complete."

    Write-Host "[*] Updating host files in $DEST ..."
    if (-not (Test-Path $DEST)) { New-Item -ItemType Directory -Path $DEST -Force | Out-Null }

    # Copy new host files
    $hostSrc = Join-Path $TMP "host"
    Get-ChildItem -Path $hostSrc -File | ForEach-Object {
        Copy-Item $_.FullName -Destination $DEST -Force
    }

    # Copy updater scripts
    Copy-Item (Join-Path $TMP "scripts\detect_extension_id.py") -Destination $DEST -Force -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $TMP "scripts\install_config.py") -Destination $DEST -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Host files updated."

    # Re-register native messaging host to pick up any manifest changes
    Write-Host "[*] Re-registering native messaging host..."
    $regScript = Join-Path $TMP "scripts\register_host_windows.py"
    if (Test-Path $regScript) {
        python "$regScript" "$DEST" 2>$null
    }

    Write-Host ""
    Write-Host "=================================================="
    Write-Host "  OK  FlashYT updated successfully!"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host " Next steps:"
    Write-Host "  1) Reload the FlashYT extension:"
    Write-Host "     chrome://extensions  -> click the refresh icon on FlashYT"
    Write-Host "  2) Open any YouTube video and click 'Download'."
    Write-Host ""
} finally {
    Remove-Item -Path $TMP -Recurse -Force -ErrorAction SilentlyContinue
}
