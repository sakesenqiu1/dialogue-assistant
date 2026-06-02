@echo off
chcp 65001 >nul 2>&1
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
  echo [提示] 请先在 .env 中把 DEEPSEEK_API_KEY 改成你的 DeepSeek 密钥。
  echo        保存后关闭记事本，本程序将继续启动（AI 功能需有效密钥）。
  echo.
  notepad .env
)

echo.
echo ========================================
echo   暖心对话助手（便携版，无需安装 Python）
echo ========================================
echo   配置：编辑项目根目录 .env 中的 DEEPSEEK_API_KEY
echo   使用：浏览器打开下面显示的地址
echo   关闭本窗口 = 停止服务
echo ========================================
echo.

"%PYEXE%" start_server.py

call "%~dp0stop_server.bat" silent
pause
