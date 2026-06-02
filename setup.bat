@echo off
cd /d "%~dp0"
call "%~dp0_init.bat"
if errorlevel 1 exit /b 1

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [setup] Created .env from .env.example - please set DEEPSEEK_API_KEY
)

if not exist "data" mkdir "data"

set "PYEXE=%~dp0runtime\python\python.exe"
if exist "%PYEXE%" (
  "%PYEXE%" -c "import fastapi,uvicorn,sqlalchemy" 2>nul
  if not errorlevel 1 exit /b 0
  echo [setup] Dependencies incomplete, continuing install...
)

echo.
echo [setup] First run: downloading embedded Python (needs internet, 1-3 min)...
echo.
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
if errorlevel 1 (
  echo.
  echo [setup] Failed. Check network, then run run.bat again.
  exit /b 1
)
echo.
echo [setup] Ready.
exit /b 0
