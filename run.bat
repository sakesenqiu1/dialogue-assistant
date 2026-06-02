@echo off
cd /d "%~dp0"

call "%~dp0stop_server.bat" silent

call "%~dp0setup.bat"
if errorlevel 1 (
  pause
  exit /b 1
)

set "PYEXE=%~dp0runtime\python\python.exe"

findstr /I /C:"your_api_key_here" ".env" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo [TIP] Set DEEPSEEK_API_KEY in .env, save, then this window continues.
  echo.
  notepad .env
)

echo.
echo ========================================
echo   Warm Dialogue Assistant
echo ========================================
echo   Config: .env -^> DEEPSEEK_API_KEY
echo   Open the URL shown below in your browser
echo   Close this window to stop the server
echo ========================================
echo.

"%PYEXE%" start_server.py

call "%~dp0stop_server.bat" silent
pause
