# Changelog

## [2.2.5] - 2026-03-16
### Fixed
- **Windows Install Flow**: Rewrote the installer finish screen to provide explicit "Load Unpacked" instructions. Modern Chromium browsers block silent extension installations, so guiding users to manually load it is the only 100% reliable method.
- **Windows `ffmpeg` Integrity**: Verified that `ffmpeg.exe` is successfully bundled into the setup binary.
- **Linux Chrome Snap Path**: Verified that `install.sh` correctly links the native messaging manifest inside Snap-installed versions of Chrome.
- **Mac/Linux Scripts Cleanup**: Removed dead auto-detection code that incorrectly fetched temporary Extension IDs. Hardcoded the permanent production Extension ID (`epfpikjgfkpagepdhbancgmeganikbgo`) directly.
- **Python Check Enhancement**: Added a strict Python 3.8+ check in `install.sh` that prints explicit OS-specific upgrade instructions instead of silently crashing `pip`.

## [2.2.4] - 2026-03-16
### Fixed
- **Windows Permissions Crash**: Fixed a critical bug where `cookies.py` attempted to write to `C:\Program Files\` (read-only), causing a silent crash right after clicking Download. Cookies are now written to `%APPDATA%\YouTubeNativeExt`.
- **Zombie Host Processes**: Fixed an issue where the Windows installer started `host.exe` manually. Browsers spawn the host dynamically, so the manual process would linger as a zombie and lock the log files forever.
- **Removed Registry Setup**: Fully removed the registry auto-install keys from Inno Setup as they were being blocked by Brave/Chrome Enterprise policies and causing confusion.

## [2.2.3] - 2026-03-14
### Fixed
- **Fixed PR Creation**: Corrected GitHub Actions workflow permissions preventing automatic yt-dlp update PRs.
## [2.2.2] - 2026-03-04
### Fixed
- **Emergency Patch**: Successfully landed all missing surgical fixes in `install.sh` and `uninstall.sh` (Python 3.8 check, Snap Chrome path, Fixed ID registration).
- **Prefetch Restoration**: Reverted the quality fetching logic to the snappy v2.1.9 flow, eliminating the "Still fetching formats" delay while keeping v2.2.2 stability features.
- **Cleanup**: Verified absolute removal of any potential merge conflict remnants.

## [2.2.1] - 2026-03-04

## [2.2.0] - 2026-03-04 - The "One-Click" Update
### Added
- **Windows One-Click Install**: Rewrote the installer to automatically load the extension in Chrome, Brave, and Edge via Registry. No more "Load Unpacked" required.
- **Auto-Update System**: Extension now detects new releases and shows a banner for easy updates.
- **System Tray Icon**: Windows users now have a tray icon for logs and status monitoring.
- **High-Definition Support**: Restored reliable 4K and 8K Ultra HD downloads.
- **Security**: Extension now uses a fixed cryptographic key, ensuring a stable Extension ID across all devices.

### Changed
- Refactored `install.sh` to prevent `curl | bash` piping (which caused empty ID bugs).
- Moved all instructions to a 3-step modern setup flow.

### Fixed
- Fixed "MoveFile failed (Access Denied)" error on Windows updates by force-closing the background host.
- Fixed "File Not Found" cascade error in Windows installer.
