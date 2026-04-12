# OpenAGI Setup Guide

## Quick Setup

```bash
setup.bat
```

This will:
1. Install all Python dependencies
2. Create `.env` file with API keys
3. Create required directories
4. Run health check

## Manual Setup

### 1. Install Dependencies

```bash
# Core dependencies (required)
pip install groq openai chromadb sentence-transformers \
    beautifulsoup4 requests python-dotenv feedparser pyyaml jinja2

# Web UI mode (required for web)
pip install fastapi uvicorn websockets qrcode[pil] Pillow

# Voice mode (optional)
pip install pvporcupine edge-tts pyaudio sounddevice soundfile

# Google integration (optional)
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
    google-api-python-client

# Computer control (optional)
pip install psutil plyer faiss-cpu
```

### 2. Configure Environment

Create `.env` file:

```env
# Required
GROQ_API_KEY=your_groq_key
NVIDIA_API_KEY=your_nvidia_key

# Optional - Telegram bot mode
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Optional - Voice settings
TTS_VOICE=en-GB-RyanNeural
WAKE_WORD=jarvis

# Optional - Web UI
WEBUI_PORT=8765

# Optional - User context
USER_CITY=Kuala Lumpur
USER_COUNTRY=Malaysia

# Model settings
NVIDIA_MAIN_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1
```

### 3. Run OpenAGI

#### CLI Mode (default)
```bash
python kernel.py
# or
python kernel.py cli
```

#### Web UI Mode
```bash
python kernel.py web
# Opens on http://localhost:8765
# QR code displayed for mobile access
```

#### Telegram Bot Mode
```bash
python kernel.py telegram
```

#### Voice Mode (requires voice dependencies)
```bash
python kernel.py voice
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `No module named 'fastapi'` | Run `pip install fastapi uvicorn` |
| `No module named 'sounddevice'` | Run `pip install sounddevice` (voice mode only) |
| `No module named 'qrcode'` | Run `pip install qrcode[pil]` |
| Web UI doesn't open | Check `WEBUI_PORT` isn't in use |
| Voice not working | Check microphone permissions |

## Run Tests

```bash
python test_comprehensive.py
```
