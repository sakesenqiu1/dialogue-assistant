@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

call "%~dp0stop_server.bat" silent

set "PYEXE=%~dp0runtime\python\python.exe"
if not exist "%PYEXE%" (
  echo.
  echo [错误] 未找到内置 Python：runtime\python\python.exe
  echo 请在本机有网络时，右键「用 PowerShell 运行」build_portable.ps1 生成运行时。
  echo 或将已打包好的完整 222 文件夹原样复制过来。
  echo.
  pause
  exit /b 1
)

if not exist ".env" copy /Y ".env.example" ".env"

echo.
echo ========================================
echo   暖心对话助手（便携版，无需安装 Python）
echo ========================================
echo   1. 首次使用请编辑 .env 填写 DEEPSEEK_API_KEY
echo   2. 浏览器打开下面显示的地址
echo   关闭本窗口 = 停止服务
echo ========================================
echo.

"%PYEXE%" start_server.py

call "%~dp0stop_server.bat" silent
pause
