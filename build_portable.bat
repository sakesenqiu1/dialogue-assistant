@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo 正在构建内置 Python 环境，需要联网，请稍候...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
if errorlevel 1 (
  echo 构建失败。
  pause
  exit /b 1
)
echo.
echo 构建成功。现在可以双击 run.bat 启动，也可将整个 222 文件夹复制到其他电脑。
pause
