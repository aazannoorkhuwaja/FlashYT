# Changelog

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
