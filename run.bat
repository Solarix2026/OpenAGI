@echo off
:: OpenAGI Launcher - automatically uses venv Python
title OpenAGI v5.0

set VENV_DIR=%~dp0venv
set PYTHON=%VENV_DIR%\Scripts\python.exe

if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first to create venv and install dependencies.
    pause
    exit /b 1
)

:: Check if fastapi is installed in venv
"%PYTHON%" -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [INFO] Installing web dependencies...
    "%PYTHON%" -m pip install fastapi uvicorn websockets qrcode[pil] -q
)

if "%1"=="" (
    echo ============================================
    echo OpenAGI v5.0 Launcher
    echo ============================================
    echo.
    echo Usage: run.bat [mode]
    echo.
    echo Modes:
    echo   cli       ^| Command line mode (default)
    echo   web       ^| Web UI with QR code
    echo   telegram  ^| Telegram bot mode
    echo   voice     ^| Voice/Jarvis mode
    echo.
    echo ============================================
    set /p MODE="Enter mode [cli]: "
    if "!MODE!"=="" set MODE=cli
) else (
    set MODE=%1
)

echo.
echo Starting OpenAGI in %MODE% mode...
echo.

"%PYTHON%" kernel.py %MODE%

pause
