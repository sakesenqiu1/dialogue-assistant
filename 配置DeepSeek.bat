@echo off
cd /d "%~dp0"
call "%~dp0setup.bat"
echo Edit DEEPSEEK_API_KEY in Notepad, then save and close.
echo.
notepad .env
echo.
echo Done. Double-click run.bat to start.
pause
