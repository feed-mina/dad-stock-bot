@echo off
cd /d "%~dp0"
set PYTHONPATH=src
python -m dad_stock_bot gui
echo.
echo If no window opened, read the messages above.
pause
