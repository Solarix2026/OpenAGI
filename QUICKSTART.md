# OpenAGI v5 - Quick Start Guide

## Prerequisites

Make sure you have Python 3.11+ installed and all dependencies:

```bash
pip install pydantic>=2.0 pydantic-settings fastapi>=0.110 uvicorn[standard] httpx \
  structlog python-dotenv faiss-cpu numpy trafilatura playwright groq openai \
  sqlite-utils sentence-transformers pytest pytest-asyncio
```

## Configuration

1. Copy the environment template:
```bash
cp config/.env.template config/.env
```

2. Edit `config/.env` and add your API keys:
- NVIDIA_NIM_API_KEY (get from https://build.nvidia.com/)
- GROQ_API_KEY (get from https://console.groq.com/)
- OPENAI_API_KEY (get from https://platform.openai.com/)

## Starting the Server

### Option 1: Start API Server (Default)
```bash
python main.py
```

This starts the FastAPI server on `http://0.0.0.0:8000`

### Option 2: Interactive CLI Mode
```bash
python main.py --chat
```

This starts an interactive chat session in your terminal.

### Option 3: System Health Check
```bash
python main.py --check
```

This runs a diagnostic check of all components.

## Testing the API

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Tools
```bash
curl http://localhost:8000/tools
```

### List Available Skills
```bash
curl http://localhost:8000/skills
```

### Memory Recall
```bash
curl -X POST http://localhost:8000/memory/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "layer": "working"}'
```

## WebSocket Testing

You can test the WebSocket endpoint using a simple Python script:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Send a message
        message = {
            "type": "message",
            "content": "Hello, can you help me?",
            "session_id": "test-session-001"
        }
        await websocket.send(json.dumps(message))

        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {data['type']} - {data.get('content', '')}")

            if data['type'] == 'done':
                break

asyncio.run(test_websocket())
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/core/ -v
python -m pytest tests/tools/ -v
python -m pytest tests/agents/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running from the project root:
```bash
cd /path/to/openagi_v2
python main.py
```

### Port Already in Use
Change the port in `config/.env`:
```
API_PORT=8001
```

### API Key Issues
Make sure your API keys are valid and have sufficient credits.

## Next Steps

1. Configure your API keys in `config/.env`
2. Start the server: `python main.py`
3. Test the health endpoint: `curl http://localhost:8000/health`
4. Try the WebSocket interface or interactive CLI mode
5. Explore the available tools and skills
