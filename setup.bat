@echo off
REM OpenAGI v5 Setup Script
REM This script helps you set up credentials and push to GitHub

echo ============================================================
echo OpenAGI v5 - Setup and GitHub Push
echo ============================================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo [1/5] Initializing Git repository...
    git init
    git add .
    git commit -m "Initial commit: OpenAGI v5 Phase 1"
    echo.
) else (
    echo [1/5] Git repository already initialized.
    echo.
)

REM Check if remote is set
git remote -v | findstr "ApeironAILab" >nul
if %errorlevel% neq 0 (
    echo [2/5] Adding GitHub remote...
    git remote add origin https://github.com/ApeironAILab/OpenAGI.git
    echo.
) else (
    echo [2/5] GitHub remote already configured.
    echo.
)

REM Check if .env file exists
if not exist "config\.env" (
    echo [3/5] Creating .env file from template...
    copy config\.env.template config\.env
    echo.
    echo IMPORTANT: Edit config\.env and add your API keys:
    echo   - NVIDIA_NIM_API_KEY (get from https://build.nvidia.com/)
    echo   - GROQ_API_KEY (get from https://console.groq.com/)
    echo   - OPENAI_API_KEY (get from https://platform.openai.com/)
    echo.
    echo Press any key to continue after adding your API keys...
    pause >nul
    echo.
) else (
    echo [3/5] .env file already exists.
    echo.
)

REM Check if dependencies are installed
echo [4/5] Checking dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install pydantic>=2.0 pydantic-settings fastapi>=0.110 uvicorn[standard] httpx structlog python-dotenv faiss-cpu numpy trafilatura playwright groq openai sqlite-utils sentence-transformers pytest pytest-asyncio
    echo.
) else (
    echo Dependencies already installed.
    echo.
)

REM Run system tests
echo [5/5] Running system tests...
python test_system.py
if %errorlevel% neq 0 (
    echo.
    echo WARNING: System tests failed. Please check the errors above.
    echo.
)

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Edit config\.env and add your API keys
echo   2. Run: python main.py
echo   3. Test: curl http://localhost:8000/health
echo.
echo To push to GitHub:
echo   git add .
echo   git commit -m "feat: OpenAGI v5 Phase 1 complete"
echo   git push origin main
echo.
echo Press any key to exit...
pause >nul
