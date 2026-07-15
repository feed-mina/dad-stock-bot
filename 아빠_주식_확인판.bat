@echo off
chcp 65001 >nul
title 아빠 주식 확인판
cd /d "%~dp0"
set "PYTHONPATH=src"

rem 정상 동작하는 python 을 먼저 시도
python -m dad_stock_bot gui
if not errorlevel 1 goto :eof

rem python 이 없으면 py 런처로 재시도
echo.
echo (python 을 찾지 못해 py 런처로 다시 시도합니다...)
py -m dad_stock_bot gui
if not errorlevel 1 goto :eof

echo.
echo ============================================
echo  프로그램을 실행하지 못했습니다.
echo  위에 표시된 오류 메시지를 확인해 주세요.
echo ============================================
pause
