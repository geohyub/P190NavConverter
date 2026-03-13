@echo off
echo ============================================
echo   P190 NavConverter - Build Executable
echo ============================================

cd /d "%~dp0"

:: Check PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller not found. Install with: pip install pyinstaller
    pause
    exit /b 1
)

:: Build
echo Building executable...
python -m PyInstaller P190_NavConverter.spec --noconfirm

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo ============================================
echo   Build complete! Check dist\ folder
echo ============================================
pause
