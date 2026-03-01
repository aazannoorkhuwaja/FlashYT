[Setup]
AppName=FlashYT
AppVersion=2.1.1
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
var
  Work, Token: String;
  PosComma, I: Integer;
begin
  Result := False;
  Work := Trim(Value);
  if Work = '' then
    Exit;

  while Work <> '' do
  begin
    PosComma := Pos(',', Work);
    if PosComma > 0 then
    begin
      Token := Trim(Copy(Work, 1, PosComma - 1));
      Work := Trim(Copy(Work, PosComma + 1, MaxInt));
    end
    else
    begin
      Token := Trim(Work);
      Work := '';
    end;

    if Length(Token) <> 32 then
      Exit;

    for I := 1 to 32 do
    begin
      if not ((Token[I] >= 'a') and (Token[I] <= 'p')) then
        Exit;
    end;
  end;

  Result := True;
end;

{ Utility to execute detect_ext.exe silently and read stdout }
function RunDetectExtAndGetStdout(var StdOutStr: String): Boolean;
var
  TmpOutFile, TmpExeFile: String;
  ResultCode: Integer;
  Lines: TArrayOfString;
begin
  Result := False;
  StdOutStr := '';
  TmpOutFile := ExpandConstant('{tmp}\detect_out.txt');
  TmpExeFile := ExpandConstant('{tmp}\detect_ext.exe');
  
  { Extract detect_ext.exe early purely for this Code step before main installation }
  try
    ExtractTemporaryFile('detect_ext.exe');
  except
    { If it fails to extract (e.g. missing from [Files]), abort early }
    Exit;
  end;
  
  if Exec(ExpandConstant('{cmd}'), '/c ""' + TmpExeFile + '"" --all-csv > ""' + TmpOutFile + '""', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    { detect_ext.exe returns 0 if found, 1 if missing }
    if ResultCode = 0 then
    begin
      if LoadStringsFromFile(TmpOutFile, Lines) then
      begin
        if GetArrayLength(Lines) > 0 then
        begin
          StdOutStr := Trim(Lines[0]);
          if IsValidExtensionIDsCSV(StdOutStr) then
            Result := True;
        end;
      end;
    end;
  end;
  
  DeleteFile(TmpOutFile);
end;

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
