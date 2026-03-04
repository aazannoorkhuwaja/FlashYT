[Code]
procedure InitializeWizard;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{cmd}'), '/c taskkill /f /im host.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
