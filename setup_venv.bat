@echo off
REM OpenAGI v5 - Virtual Environment Setup Script
REM This script sets up a virtual environment and installs all dependencies

echo ============================================================
echo OpenAGI v5 - Virtual Environment Setup
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/6] Python found
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/6] Creating virtual environment...
    python -m venv venv
    echo.
) else (
    echo [2/6] Virtual environment already exists
    echo.
)

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo [5/6] Installing dependencies...
echo This may take a few minutes...
pip install pydantic>=2.0 pydantic-settings fastapi>=0.110 uvicorn[standard] httpx structlog python-dotenv faiss-cpu numpy trafilatura playwright groq openai sqlite-utils sentence-transformers pytest pytest-asyncio websockets
echo.

REM Install Playwright browsers
echo [6/6] Installing Playwright browsers...
playwright install chromium
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Virtual environment created: venv\
echo.
echo To activate the virtual environment:
echo   venv\Scripts\activate.bat
echo.
echo To start the API server:
echo   python main.py
echo.
echo To start CLI chat:
echo   python main.py chat
echo.
echo To run system check:
echo   python main.py check
echo.
echo To deactivate the virtual environment:
echo   deactivate
echo.
echo Press any key to exit...
pause >nul
