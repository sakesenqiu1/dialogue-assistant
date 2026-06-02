@echo off
REM Resolve PowerShell when "powershell" is not on PATH
set "PWSH=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PWSH%" set "PWSH=%WINDIR%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PWSH%" if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" set "PWSH=%ProgramFiles%\PowerShell\7\pwsh.exe"
if not exist "%PWSH%" (
  echo.
  echo [ERROR] Cannot find PowerShell.
  echo         Try: Win+X -^> Windows PowerShell, then run:
  echo         cd /d "%~dp0"
  echo         build_portable.ps1
  echo.
  exit /b 1
)
exit /b 0
