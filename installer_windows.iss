[Setup]
AppName=FlashYT
AppVersion=2.2.7
AppPublisher=Aazan Noor Khuwaja
AppPublisherURL=https://github.com/aazannoorkhuwaja/FlashYT
DefaultDirName={autopf}\FlashYT
DefaultGroupName=FlashYT
OutputDir=dist
OutputBaseFilename=FlashYT-setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableWelcomePage=no

[InstallDelete]
Type: files; Name: "{app}\host.exe"
Type: files; Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\YouTubeDownloader.vbs"

[Files]
Source: "host\dist\host.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "host\com.youtube.native.ext.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\detect_ext.exe"; DestDir: "{tmp}"; Flags: dontcopy
Source: "scripts\dist\detect_ext.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\register_host_windows.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "extension\*"; DestDir: "{localappdata}\Programs\FlashYT\extension"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Start FlashYT"; Filename: "{app}\host.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall FlashYT"; Filename: "{uninstallexe}"

[Registry]

[Run]
; Registration happens silently below
Filename: "{app}\register_host_windows.exe"; Parameters: """{app}"" ""epfpikjgfkpagepdhbancgmeganikbgo"""; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Registering Native Host Connection"
; Scheduled silent update task 
Filename: "schtasks.exe"; Parameters: "/create /tn ""FlashYT-Update"" /tr ""{app}\yt-dlp.exe -U"" /sc weekly /d MON /st 10:00 /f"; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Creating Update Scheduler"

[UninstallRun]
; Kill process gracefully if running (including full process tree)
Filename: "taskkill.exe"; Parameters: "/f /t /im host.exe"; Flags: runhidden waituntilterminated
; Delete scheduled task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""FlashYT-Update"" /f"; Flags: runhidden
; Extra cleanup: remove native host manifest
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{userappdata}\YouTubeNativeExt"""; Flags: runhidden waituntilterminated

[UninstallDelete]
; Remove extension files copied to LocalAppData
Type: filesandordirs; Name: "{localappdata}\Programs\FlashYT"
Type: files; Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\YouTubeDownloader.vbs"

[Code]

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // Kill any running FlashYT host process before installation
  // This prevents "MoveFile failed; code 5: Access is denied" on update/reinstall
  Exec('taskkill.exe', '/F /IM host.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // ResultCode 0 = process killed, 128 = process not found (both are fine)
  // Sleep 1 second to ensure Windows fully releases the file lock
  Sleep(1000);
  Result := ''; // Empty string = no error, proceed with installation
end;

procedure InitializeWizard;
begin
  WizardForm.FinishedLabel.Caption :=
    '✅ FlashYT host installed successfully!' + #13#10 + #13#10 +
    'To complete setup, load the extension in your browser:' + #13#10 +
    '1. Open your browser extensions page:' + #13#10 +
    '   - Chrome: chrome://extensions' + #13#10 +
    '   - Brave: brave://extensions' + #13#10 +
    '   - Edge: edge://extensions' + #13#10 +
    '2. Turn ON "Developer mode" (toggle in top right)' + #13#10 +
    '3. Click "Load unpacked"' + #13#10 +
    '4. Select this exact folder:' + #13#10 +
    '   ' + ExpandConstant('{localappdata}\Programs\FlashYT\extension') + #13#10 + #13#10 +
    '5. Open any YouTube video and click the ⚡ Download button!' + #13#10 +
    'Need help? github.com/aazannoorkhuwaja/FlashYT/issues';
end;
