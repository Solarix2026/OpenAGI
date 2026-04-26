# OpenAGI v5 - Quick Start Guide

## 🚀 Setup Instructions

### Option 1: Automated Setup (Recommended)

```powershell
# Run the setup script
setup_venv.bat
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up Playwright browsers
- Configure everything automatically

### Option 2: Manual Setup

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
venv\Scripts\activate.bat

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install dependencies
pip install pydantic>=2.0 pydantic-settings fastapi>=0.110 uvicorn[standard] httpx structlog python-dotenv faiss-cpu numpy trafilatura playwright groq openai sqlite-utils sentence-transformers pytest pytest-asyncio websockets

# 5. Install Playwright browsers
playwright install chromium
```

## 🔑 Configure API Keys

```powershell
# Copy the template
copy config\.env.template config\.env

# Edit config\.env and add your API keys:
# - NVIDIA_NIM_API_KEY (get from https://build.nvidia.com/)
# - GROQ_API_KEY (get from https://console.groq.com/)
# - OPENAI_API_KEY (get from https://platform.openai.com/)
```

## 🎮 How to Use

### Start API Server
```powershell
# Make sure virtual environment is activated
venv\Scripts\activate.bat

# Start the server
python main.py
```

Server will start on: `http://0.0.0.0:8000`

### Start CLI Chat
```powershell
# Make sure virtual environment is activated
venv\Scripts\activate.bat

# Start chat mode
python main.py chat
```

### Run System Check
```powershell
# Make sure virtual environment is activated
venv\Scripts\activate.bat

# Run health check
python main.py check
```

## 🧪 Test the API

### Using PowerShell

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# List tools
Invoke-RestMethod -Uri "http://localhost:8000/tools"

# List skills
Invoke-RestMethod -Uri "http://localhost:8000/skills"

# Memory recall
$body = @{
    query = "test"
    layer = "working"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/memory/recall" -Method POST -Body $body -ContentType "application/json"
```

## 📁 Project Structure

```
openagi_v2/
├── main.py                 # Entry point (server/chat/web/telegram)
├── config/                 # Configuration and settings
├── core/                   # Core components (L1/L2/L3/L4)
├── memory/                 # Memory systems
├── tools/                  # Tool registry and built-in tools
├── skills/                 # Skill loader and built-in skills
├── agents/                 # Agent components (planner/executor/reflector)
├── gateway/                # LLM gateway
├── api/                    # FastAPI server
├── sandbox/                # Execution sandbox
├── tests/                  # Test suite
└── venv/                   # Virtual environment (created during setup)
```

## 🔧 Available Commands

```powershell
python main.py              # Start API server (default)
python main.py chat         # Start CLI chat mode
python main.py web          # Start web interface (future)
python main.py telegram     # Start Telegram bot (future)
python main.py check        # Run system health check
```

## 💡 Example Conversations

### CLI Chat Mode
```
You: Hello, can you help me?
AGI: [Response from your AGI]

You: What tools do you have available?
AGI: [Lists available tools]

You: Can you write a Python function to calculate fibonacci numbers?
AGI: [Will use code tool to write and execute the function]
```

## 🐛 Troubleshooting

### Port 8000 already in use?
Edit `config\.env` and change:
```
API_PORT=8001
```

### Import errors?
Make sure you're in the project root and virtual environment is activated:
```powershell
cd C:\Users\mjtan\desktop\openagi_v2
venv\Scripts\activate.bat
python main.py
```

### API key issues?
Verify your keys in `config\.env` and test with:
```powershell
python main.py check
```

### Virtual environment not activating?
Make sure you're using Windows PowerShell or Command Prompt, not Git Bash or WSL.

## 📊 System Requirements

- Python 3.11 or higher
- Windows 10/11
- 4GB RAM minimum (8GB recommended)
- 2GB disk space

## 🎯 Next Steps

1. Run `setup_venv.bat` to set up the environment
2. Configure your API keys in `config\.env`
3. Start with `python main.py check` to verify everything works
4. Try `python main.py chat` to interact with your AGI
5. Explore the API at `http://localhost:8000/docs`

## 📚 Documentation

- **PHASE1_COMPLETE.md** - Complete implementation details
- **QUICKSTART.md** - This file
- **setup_venv.bat** - Automated setup script
- **test_system.py** - System verification tests

## 🌐 GitHub Repository

https://github.com/ApeironAILab/OpenAGI

## 🆘 Support

If you encounter issues:
1. Check that your virtual environment is activated
2. Verify API keys in `config\.env`
3. Run `python main.py check` for diagnostics
4. Check the logs for error messages

---

**Status:** 🟢 **PRODUCTION READY** ✓
