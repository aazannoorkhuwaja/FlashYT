[Setup]
AppName=FlashYT
AppVersion=2.2.3
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
; ── Chrome: Tell Chrome to load FlashYT extension from local folder ──
Root: HKCU; Subkey: "Software\Google\Chrome\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\Programs\FlashYT\extension"; Flags: createvalueifdoesntexist uninsdeletekey
Root: HKCU; Subkey: "Software\Google\Chrome\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.3"; Flags: createvalueifdoesntexist uninsdeletekey

; ── Brave: Same extension, different registry path ──
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\Programs\FlashYT\extension"; Flags: createvalueifdoesntexist uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.3"; Flags: createvalueifdoesntexist uninsdeletekey

; ── Edge: Same extension, different registry path ──
Root: HKCU; Subkey: "Software\Microsoft\Edge\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\Programs\FlashYT\extension"; Flags: createvalueifdoesntexist uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.3"; Flags: createvalueifdoesntexist uninsdeletekey

[Run]
; Registration happens silently below
Filename: "{app}\register_host_windows.exe"; Parameters: """{app}"" ""epfpikjgfkpagepdhbancgmeganikbgo"""; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Registering Native Host Connection"
; Scheduled silent update task 
Filename: "schtasks.exe"; Parameters: "/create /tn ""FlashYT-Update"" /tr ""{app}\yt-dlp.exe -U"" /sc weekly /d MON /st 10:00 /f"; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Creating Update Scheduler"

[UninstallRun]
; Kill process gracefully if running
Filename: "taskkill.exe"; Parameters: "/f /im host.exe"; Flags: runhidden waituntilterminated
; Delete scheduled task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""FlashYT-Update"" /f"; Flags: runhidden
; Extra cleanup
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{userappdata}\YouTubeNativeExt"""; Flags: runhidden waituntilterminated

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

procedure LaunchHostSafely();
var
  HostPath: String;
  ResultCode: Integer;
begin
  // {app} is the actual install directory (e.g. C:\Program Files\FlashYT)
  // This MUST match where the [Files] section installs host.exe (DestDir: "{app}")
  HostPath := ExpandConstant('{app}\host.exe');
  if FileExists(HostPath) then
  begin
    Exec(HostPath, '', '', SW_HIDE, ewNoWait, ResultCode);
  end
  else
  begin
    MsgBox(
      'FlashYT installed but host.exe was not found at:' + #13#10 +
      HostPath + #13#10#10 +
      'Please restart your computer, or double-click host.exe from the install folder.' + #13#10 +
      'If this problem persists, please reinstall FlashYT.',
      mbInformation, MB_OK
    );
  end;
end;

// EnableChromeDeveloperMode() was removed — editing Chrome Preferences at install
// time is unreliable because Chrome overwrites the file when it exits.
// Developer mode is now handled via clear user instructions in the finish page.

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    LaunchHostSafely();
  end;
end;

procedure InitializeWizard;
begin
  WizardForm.FinishedLabel.Caption :=
    '✅ FlashYT is installed!' + #13#10 + #13#10 +
    'STEP 1 — Close your browser completely (all windows), then reopen it.' + #13#10 +
    'The FlashYT extension should appear automatically.' + #13#10 + #13#10 +
    '— If the extension does NOT appear —' + #13#10 +
    '1. Open chrome://extensions in your browser' + #13#10 +
    '2. Turn ON "Developer mode" (top-right toggle)' + #13#10 +
    '3. Click "Load unpacked"' + #13#10 +
    '4. Select this folder: ' + ExpandConstant('{localappdata}\Programs\FlashYT\extension') + #13#10 +
    '5. Reload any YouTube page' + #13#10 + #13#10 +
    'Then visit any YouTube video and click the ⚡ Download button!' + #13#10 +
    'Need help? github.com/aazannoorkhuwaja/FlashYT/issues';
end;
