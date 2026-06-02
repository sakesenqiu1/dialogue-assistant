@echo off
cd /d "%~dp0"

if exist "data\server.pid" (
  set /p SPID=<data\server.pid
  if defined SPID taskkill /F /PID %SPID% >nul 2>&1
)

echo Stopping servers on ports 8000 8001 8765 8877 ...
for %%P in (8000 8001 8765 8877) do (
  for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr "LISTENING" ^| findstr ":%%P "') do (
    taskkill /F /PID %%a >nul 2>&1
  )
)

if exist "data\server.pid" del /f /q "data\server.pid" >nul 2>&1
if exist "data\server.port" del /f /q "data\server.port" >nul 2>&1

if /i "%~1"=="silent" goto :eof
echo Done. You can run run.bat again.
pause
