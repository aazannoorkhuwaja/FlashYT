[Setup]
AppName=YouTube Native Downloader
AppVersion=1.0.0
AppPublisher=Aazan Noor Khuwaja
AppPublisherURL=https://github.com/aazannoorkhuwaja/youtube-native-ext
DefaultDirName={autopf}\YouTubeNativeDownloader
DefaultGroupName=YouTube Native Downloader
OutputDir=dist
OutputBaseFilename=youtube-native-downloader-setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableWelcomePage=no

[Files]
Source: "host\dist\host.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\yt-dlp.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "host\com.youtube.native.ext.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\detect_ext.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "scripts\dist\register_host_windows.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Start YouTube Downloader"; Filename: "{app}\host.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall YouTube Downloader"; Filename: "{uninstallexe}"

[Run]
; Step 1 + 2: Handle extension detection via Code section before registering
; Step 3: Registration happens silently below
Filename: "{app}\register_host_windows.exe"; Parameters: """{app}"" ""{code:GetExtensionID}"""; Flags: runhidden runasoriginaluser; Description: "Registering Native Host Connection"
; Step 4: Scheduled silent update task 
Filename: "schtasks.exe"; Parameters: "/create /tn ""YouTubeNativeDownloader-Update"" /tr ""'{app}\yt-dlp.exe' --update"" /sc weekly /d MON /st 10:00 /f"; Flags: runhidden runasoriginaluser; Description: "Creating Update Scheduler"
; Step 5: Start immediately
Filename: "{app}\host.exe"; Flags: nowait postinstall runasoriginaluser; Description: "Start YouTube Native Downloader"

[UninstallRun]
; Kill process gracefully if running
Filename: "taskkill.exe"; Parameters: "/f /im host.exe"; Flags: runhidden waituntilterminated
; Delete scheduled task
Filename: "schtasks.exe"; Parameters: "/delete /tn ""YouTubeNativeDownloader-Update"" /f"; Flags: runhidden
; Extra cleanup
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{userappdata}\YouTubeNativeExt"""; Flags: runhidden waituntilterminated

[Code]
var
  UserExtensionID: String;
  ExtensionDetectionFailed: Boolean;

{ Utility to execute our bundled PyInstaller CLI tool silently and read stdout }
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
  
  if Exec(ExpandConstant('{cmd}'), '/c ""' + TmpExeFile + '"" > ""' + TmpOutFile + '""', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    { detect_ext.exe returns 0 if found, 1 if missing }
    if ResultCode = 0 then
    begin
      if LoadStringsFromFile(TmpOutFile, Lines) then
      begin
        if GetArrayLength(Lines) > 0 then
        begin
          StdOutStr := Trim(Lines[0]);
          if Length(StdOutStr) = 32 then
            Result := True;
        end;
      end;
    end;
  end;
  
  DeleteFile(TmpOutFile);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  DetectResult: String;
begin
  Result := True;

  if CurPageID = wpReady then
  begin
    { Attempt auto-detection right before we install }
    if RunDetectExtAndGetStdout(DetectResult) then
    begin
      UserExtensionID := DetectResult;
      ExtensionDetectionFailed := False;
    end
    else
    begin
      ExtensionDetectionFailed := True;
      UserExtensionID := '';
    end;
  end;
end;

function GetExtensionID(Param: String): String;
var
  InputID: String;
  Valid: Boolean;
begin
  if not ExtensionDetectionFailed and (Length(UserExtensionID) = 32) then
  begin
    Result := UserExtensionID;
    Exit;
  end;

  Valid := False;
  InputID := '';
  
  while not Valid do
  begin
    if InputQuery('Extension Missing', 
                  'We could not auto-detect the Chrome extension.'#13#10 + 
                  'Please install the extension via chrome://extensions Developer Mode first.'#13#10#13#10 + 
                  'Paste the 32-character Extension ID below:', 
                  InputID) then
    begin
      InputID := Trim(InputID);
      if Length(InputID) = 32 then
      begin
        Valid := True;
        UserExtensionID := InputID;
      end
      else
      begin
        MsgBox('The Extension ID must be exactly 32 lowercase alphabetical characters.', mbError, MB_OK);
      end;
    end
    else
    begin
      { User cancelled prompt, fail install cleanly }
      MsgBox('Installation cannot proceed without an Extension ID.', mbError, MB_OK);
      Abort();
    end;
  end;
  
  Result := UserExtensionID;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  URL: String;
  ErrorCode: Integer;
begin
  if CurStep = ssDone then
  begin
    URL := 'https://chrome.google.com/webstore/';
    if MsgBox('Installation Complete!'#13#10#13#10'Would you like to open the Chrome Web Store to install the extension side now?', mbInformation, MB_YESNO) = idYes then
    begin
      ShellExec('open', URL, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;
