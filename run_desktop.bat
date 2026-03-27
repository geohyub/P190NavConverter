@echo off
title P190 NavConverter Desktop v2.0
cd /d "%~dp0"
python -m desktop
if errorlevel 1 pause
