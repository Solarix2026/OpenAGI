@echo off
title OpenAGI v5.0 Setup

echo ============================================
echo OpenAGI — From-Scratch Setup
echo ============================================

pip install groq openai chromadb sentence-transformers ^
    beautifulsoup4 requests python-dotenv fastapi uvicorn ^
    websockets qrcode[pil] Pillow pyttsx3 edge-tts ^
    google-auth google-auth-oauthlib google-auth-httplib2 ^
    google-api-python-client feedparser pyyaml jinja2 ^
    pyaudio sounddevice soundfile plyer psutil faiss-cpu python-pptx playwright

if not exist .env (
    echo GROQ_API_KEY=your_groq_key > .env
    echo NVIDIA_API_KEY=your_nvidia_key >> .env
    echo TELEGRAM_BOT_TOKEN= >> .env
    echo TELEGRAM_CHAT_ID= >> .env
    echo TTS_VOICE=en-GB-RyanNeural >> .env
    echo WAKE_WORD=jarvis >> .env
    echo WEBUI_PORT=8765 >> .env
    echo USER_CITY=Kuala Lumpur >> .env
    echo USER_COUNTRY=Malaysia >> .env
    echo NVIDIA_MAIN_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1 >> .env
    notepad .env
)

:: Install Playwright browsers
echo Installing Playwright browsers...
python -m playwright install chromium
)

if not exist skills mkdir skills
if not exist workspace mkdir workspace

echo.
echo Running health check...
python -c "from core.llm_gateway import check_providers; print(check_providers())"

echo.
echo ============================================
echo   python kernel.py          CLI mode
echo   python kernel.py telegram Telegram mode
echo   python kernel.py voice    Voice/Jarvis mode
echo   python kernel.py web      Web UI + QR phone
echo ============================================
pause
