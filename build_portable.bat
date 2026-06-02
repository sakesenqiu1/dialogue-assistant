@echo off
cd /d "%~dp0"
call "%~dp0_init.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
echo Building portable Python (needs internet)...
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Done. Run run.bat to start.
pause
