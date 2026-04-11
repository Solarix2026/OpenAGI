"""
llm_gateway.py — LLM routing layer

ARCHITECTURE LAW:
  Groq = routing/classification only → returns JSON, never prose
  NVIDIA NIM = all reasoning, responses, generation, summarization
  If NVIDIA fails → Groq 70B fallback (prose quality)
  If Groq fails → raise (routing is critical path)
"""
import os, logging, time, json, re
from dotenv import load_dotenv
load_dotenv()  # Load .env file
from openai import OpenAI

log = logging.getLogger("LLMGateway")

GROQ_ROUTER_MODEL = os.getenv("GROQ_ROUTER_MODEL", "llama-3.1-8b-instant")
GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"  # prose fallback
NVIDIA_MAIN_MODEL = os.getenv("NVIDIA_MAIN_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
NVIDIA_FAST_MODEL = os.getenv("NVIDIA_FAST_MODEL", "meta/llama-3.1-70b-instruct")

_groq_client = None
_nvidia_client = None


def _get_groq():
    global _groq_client
    if not _groq_client:
        from groq import Groq
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def _get_nvidia():
    global _nvidia_client
    if not _nvidia_client:
        _nvidia_client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
    return _nvidia_client


def call_groq_router(messages: list, max_tokens=250) -> str:
    """
    ROUTING ONLY. Returns JSON. Never used for prose responses.
    Fast, cheap, deterministic classification.
    """
    try:
        resp = _get_groq().chat.completions.create(
            model=GROQ_ROUTER_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,  # deterministic routing
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Groq router failed: {e}")
        raise


def call_nvidia(messages: list, max_tokens=1200, temperature=0.7, fast=False) -> str:
    """
    PRIMARY BRAIN. All responses, reasoning, generation go here.
    fast=True → use smaller/faster model for low-stakes calls.
    """
    model = NVIDIA_FAST_MODEL if fast else NVIDIA_MAIN_MODEL
    try:
        resp = _get_nvidia().chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"NVIDIA failed ({e}), falling back to Groq 70B")
        try:
            resp = _get_groq().chat.completions.create(
                model=GROQ_FALLBACK_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e2:
            log.error(f"Both LLMs failed: {e2}")
            return "I'm having trouble reaching my reasoning engine. Please try again."


def call_groq(messages: list, model=None, max_tokens=500, temperature=0.7) -> str:
    """Legacy compat — routes to NVIDIA for prose, Groq for JSON routing."""
    # Detect if this is a routing/JSON call or a prose call
    last = messages[-1].get("content", "") if messages else ""
    is_json_call = "JSON" in last or "Return JSON" in last or max_tokens <= 250

    if is_json_call:
        return call_groq_router(messages, max_tokens=max_tokens)
    return call_nvidia(messages, max_tokens=max_tokens, fast=True)


# ── Telegram helpers ──────────────────────────────────────────────

def send_telegram_alert(text: str):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096], "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        log.debug(f"Telegram send failed: {e}")


def send_telegram_file(path: str, caption=""):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": f},
                timeout=15
            )
    except Exception as e:
        log.debug(f"Telegram file send failed: {e}")


def get_telegram_updates(offset=None):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return []
    try:
        params = {"timeout": 20}
        if offset:
            params["offset"] = offset
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params=params,
            timeout=25
        )
        return r.json().get("result", [])
    except Exception:
        return []


def check_providers() -> dict:
    status = {}
    try:
        call_groq_router([{"role": "user", "content": 'Return JSON: {"ok":true}'}], max_tokens=20)
        status["groq"] = "OK"
    except Exception as e:
        status["groq"] = f"FAIL: {e}"

    try:
        call_nvidia([{"role": "user", "content": "Say OK"}], max_tokens=10, fast=True)
        status["nvidia"] = "OK"
    except Exception as e:
        status["nvidia"] = f"FAIL: {e}"

    return status
