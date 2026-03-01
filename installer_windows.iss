[Setup]
AppName=FlashYT
AppVersion=2.0.8
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

[Files]
Source: "host\dist\host.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "host\com.youtube.native.ext.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\detect_ext.exe"; DestDir: "{tmp}"; Flags: dontcopy
Source: "scripts\dist\detect_ext.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\register_host_windows.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Start FlashYT"; Filename: "{app}\host.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall FlashYT"; Filename: "{uninstallexe}"

[Run]
; Step 1 + 2: Handle extension detection via Code section before registering
; Step 3: Registration happens silently below
Filename: "{app}\register_host_windows.exe"; Parameters: """{app}"" ""{code:GetExtensionIDs}"""; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Registering Native Host Connection"
; Step 4: Scheduled silent update task 
Filename: "schtasks.exe"; Parameters: "/create /tn ""FlashYT-Update"" /tr ""{app}\yt-dlp.exe -U"" /sc weekly /d MON /st 10:00 /f"; Flags: runhidden runasoriginaluser waituntilterminated; Description: "Creating Update Scheduler"
; Step 5: Start immediately
Filename: "{app}\host.exe"; Flags: nowait postinstall runasoriginaluser; Description: "Start FlashYT Native Host"

[UninstallRun]
; Kill process gracefully if running
Filename: "taskkill.exe"; Parameters: "/f /im host.exe"; Flags: runhidden waituntilterminated
; Delete scheduled task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""FlashYT-Update"" /f"; Flags: runhidden
; Extra cleanup
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{userappdata}\YouTubeNativeExt"""; Flags: runhidden waituntilterminated

[Code]
var
  UserExtensionIDs: String;
  ExtensionDetectionFailed: Boolean;
  IDInputPage: TInputQueryWizardPage;

function IsValidExtensionIDsCSV(const Value: String): Boolean;
{... implementation omitted for brevity, keeping existing ...}

{ ... RunDetectExtAndGetStdout implementation keeping existing ... }

procedure InitializeWizard;
begin
  { Create a manual ID entry page that appears after Select Directory if auto-detection fails }
  IDInputPage := CreateInputQueryPage(wpSelectDir,
    'FlashYT Extension Configuration', 
    'The FlashYT extension was not found in your browser.',
    'Please load the extension in Chrome (Developer Mode) first, then paste its 32-character ID below.'#13#10 +
    'If you don''t have it yet, you can leave the default and fix it later in the extension settings.');

  IDInputPage.Add('FlashYT Extension ID:', False);
  IDInputPage.Values[0] := 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'; { Default fallback }
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  { Skip the manual ID page if auto-detection already succeeded }
  if (PageID = IDInputPage.ID) and (not ExtensionDetectionFailed) then
    Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  DetectResult: String;
begin
  Result := True;

  if CurPageID = wpSelectDir then
  begin
    { Attempt auto-detection early at the directory selection stage }
    if RunDetectExtAndGetStdout(DetectResult) then
    begin
      UserExtensionIDs := DetectResult;
      ExtensionDetectionFailed := False;
    end
    else
    begin
      ExtensionDetectionFailed := True;
    end;
  end;

  if CurPageID = IDInputPage.ID then
  begin
    { Validate manual entry if user is on that page }
    if not IsValidExtensionIDsCSV(IDInputPage.Values[0]) then
    begin
      MsgBox('Invalid Extension ID. It must be exactly 32 characters (a-p).', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function GetExtensionIDs(Param: String): String;
begin
  if not ExtensionDetectionFailed and (UserExtensionIDs <> '') then
    Result := UserExtensionIDs
  else
    Result := IDInputPage.Values[0];
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  URL: String;
  ErrorCode: Integer;
begin
  if CurStep = ssDone then
  begin
    URL := 'https://github.com/aazannoorkhuwaja/FlashYT#step-1--load-the-extension';
    if MsgBox(
      'FlashYT installed successfully!'#13#10#13#10 +
      'Next: reload the FlashYT extension in Chrome/Brave/Edge.'#13#10 +
      'Would you like to open the setup guide?',
      mbInformation, MB_YESNO
    ) = idYes then
    begin
      ShellExec('open', URL, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;
