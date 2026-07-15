@echo off
chcp 65001 >nul
title 아빠 주식 확인판
cd /d "%~dp0"
set "PYTHONPATH=src"
set "PY_CMD=python"
where py >nul 2>&1 && set "PY_CMD=py"
%PY_CMD% -m dad_stock_bot gui
if errorlevel 1 (
    echo.
    echo ============================================
    echo  프로그램을 실행하지 못했습니다.
    echo  파이썬^(Python^)이 설치되어 있는지 확인해 주세요.
    echo ============================================
    echo.
    pause
)
