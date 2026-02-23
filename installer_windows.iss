; Inno Setup script for One-Click YouTube Downloader (Windows)
; This gives users a familiar installer experience.

[Setup]
AppName=One-Click YouTube Downloader
AppVersion=1.0.0
DefaultDirName={autopf}\OneClickYouTubeDownloader
DefaultGroupName=One-Click YouTube Downloader
DisableDirPage=no
DisableProgramGroupPage=yes
OutputBaseFilename=OneClickYouTubeDownloaderSetup
Compression=lzma
SolidCompression=yes

[Files]
; Adjust the path to match where PyInstaller outputs your EXE
Source="dist\OneClickYouTubeDownloader\OneClickYouTubeDownloader.exe"; DestDir="{app}"; Flags: ignoreversion

[Icons]
Name="{group}\One-Click YouTube Downloader"; Filename="{app}\OneClickYouTubeDownloader.exe"
Name="{userstartup}\One-Click YouTube Downloader"; Filename="{app}\OneClickYouTubeDownloader.exe"; WorkingDir="{app}"; Tasks: autostart

[Tasks]
Name: "autostart"; Description: "Start One-Click YouTube Downloader automatically with Windows"; Flags: unchecked

[Run]
; Optionally open the Tampermonkey userscript URL after install to guide the user.
Filename="{app}\OneClickYouTubeDownloader.exe"; Description="Launch One-Click YouTube Downloader"; Flags: nowait postinstall skipifsilent
; Uncomment and adjust the URL below to point to your raw userscript:
; Filename="https://raw.githubusercontent.com/aazannoorkhuwaja/one_click_ytmp4_download/main/userscript.js"; Flags: shellexec postinstall skipifsilent

