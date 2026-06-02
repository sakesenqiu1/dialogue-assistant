@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [setup] 已从 .env.example 生成 .env，请填写 DEEPSEEK_API_KEY
)

if not exist "data" mkdir "data"

set "PYEXE=%~dp0runtime\python\python.exe"
if exist "%PYEXE%" exit /b 0

echo.
echo [setup] 首次使用：正在准备内置 Python（需联网，约 1～3 分钟）...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
if errorlevel 1 (
  echo.
  echo [setup] 环境准备失败，请检查网络后重新运行 run.bat
  exit /b 1
)
echo.
echo [setup] 环境已就绪。
exit /b 0
