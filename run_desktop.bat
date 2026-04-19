@echo off
chcp 65001 >nul
title P190 NavConverter Desktop v2.0
cd /d "%~dp0"
python -m desktop
if errorlevel 1 pause


if errorlevel 1 (
    echo.
    echo [Error] 앱 실행 실패 errorlevel=%errorlevel%
    echo 원인 확인 후 다시 실행해주세요.
    pause
    exit /b %errorlevel%
)
