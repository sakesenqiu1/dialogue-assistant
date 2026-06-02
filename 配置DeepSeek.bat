@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
call "%~dp0setup.bat"
echo 请在打开的记事本中，把 DEEPSEEK_API_KEY= 后面改成你的密钥并保存。
echo.
notepad .env
echo.
echo 保存后关闭本窗口，双击 run.bat 启动。
pause
