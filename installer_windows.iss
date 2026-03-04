[Setup]
AppName=FlashYT
AppVersion=2.2.0
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
Root: HKCU; Subkey: "Software\Google\Chrome\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.0"; Flags: createvalueifdoesntexist uninsdeletekey

; ── Brave: Same extension, different registry path ──
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\Programs\FlashYT\extension"; Flags: createvalueifdoesntexist uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.0"; Flags: createvalueifdoesntexist uninsdeletekey

; ── Edge: Same extension, different registry path ──
Root: HKCU; Subkey: "Software\Microsoft\Edge\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "path"; ValueData: "{localappdata}\Programs\FlashYT\extension"; Flags: createvalueifdoesntexist uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\Extensions\epfpikjgfkpagepdhbancgmeganikbgo"; ValueType: string; ValueName: "version"; ValueData: "2.2.0"; Flags: createvalueifdoesntexist uninsdeletekey

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
  HostPath := ExpandConstant('{localappdata}\Programs\FlashYT\host.exe');
  if FileExists(HostPath) then
  begin
    Exec(HostPath, '', '', SW_HIDE, ewNoWait, ResultCode);
  end
  else
  begin
    MsgBox(
      'FlashYT installed but could not start automatically.' + #13#10 +
      'Please restart your computer, or go to:' + #13#10 +
      ExpandConstant('{localappdata}\Programs\FlashYT\') + #13#10 +
      'and double-click host.exe to start it.' + #13#10#10 +
      'If this problem persists, please reinstall FlashYT.',
      mbInformation, MB_OK
    );
  end;
end;

procedure EnableChromeDeveloperMode();
var
  PrefsPath: String;
  PrefsContent: String;
begin
  // Standard Chrome path
  PrefsPath := ExpandConstant('{localappdata}\Google\Chrome\User Data\Default\Preferences');
  if FileExists(PrefsPath) then
  begin
    if LoadStringFromFile(PrefsPath, PrefsContent) then
    begin
      if StringChangeEx(PrefsContent, '"developer_mode":false', '"developer_mode":true', True) > 0 then
      begin
        SaveStringToFile(PrefsPath, PrefsContent, False);
      end;
    end;
  end;
  
  // Brave browser path
  PrefsPath := ExpandConstant('{localappdata}\BraveSoftware\Brave-Browser\User Data\Default\Preferences');
  if FileExists(PrefsPath) then
  begin
    if LoadStringFromFile(PrefsPath, PrefsContent) then
    begin
      StringChangeEx(PrefsContent, '"developer_mode":false', '"developer_mode":true', True);
      SaveStringToFile(PrefsPath, PrefsContent, False);
    end;
  end;
  
  // Edge browser path
  PrefsPath := ExpandConstant('{localappdata}\Microsoft\Edge\User Data\Default\Preferences');
  if FileExists(PrefsPath) then
  begin
    if LoadStringFromFile(PrefsPath, PrefsContent) then
    begin
      StringChangeEx(PrefsContent, '"developer_mode":false', '"developer_mode":true', True);
      SaveStringToFile(PrefsPath, PrefsContent, False);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    EnableChromeDeveloperMode();
    LaunchHostSafely();
  end;
end;

procedure InitializeWizard;
begin
  WizardForm.FinishedLabel.Caption :=
    '✅ FlashYT is installed!' + #13#10 + #13#10 +
    'One last step: Please close Chrome completely and reopen it.' + #13#10 +
    'FlashYT will appear in your extensions automatically.' + #13#10 + #13#10 +
    'Then visit any YouTube video and click the ⚡ Download button!';
end;
