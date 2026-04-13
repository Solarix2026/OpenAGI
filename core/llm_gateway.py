# Copyright (c) 2026 HackerTMJ
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
llm_gateway.py — LLM routing layer

ARCHITECTURE LAW:
Groq = routing/classification only → returns JSON, never prose
NVIDIA NIM = primary brain (Kimi k2.5 from NVIDIA NIM)
If NVIDIA fails → Groq 70B fallback
If Groq fails → raise (routing is critical path)
"""
import os, logging, time, json, re
from dotenv import load_dotenv
load_dotenv() # Load .env file
from openai import OpenAI

log = logging.getLogger("LLMGateway")

GROQ_ROUTER_MODEL = os.getenv("GROQ_ROUTER_MODEL", "llama-3.1-8b-instant")
GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile" # prose fallback

# NVIDIA NIM - Kimi k2.5 as primary
NVIDIA_MAIN_MODEL = os.getenv("NVIDIA_MAIN_MODEL", "moonshotai/kimi-k2.5")
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
            api_key=os.getenv("NVIDIA_API_KEY"),
            timeout=60.0 # 60s for Kimi k2.5
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
            temperature=0.0, # deterministic routing
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Groq router failed: {e}")
        raise


def call_nvidia(messages: list, max_tokens=1200, temperature=0.7, fast=False, stream_callback=None) -> str:
    """
    PRIMARY BRAIN. All responses, reasoning, generation go here.
    Uses Kimi k2.5 from NVIDIA NIM.
    fast=True → use smaller/faster model for low-stakes calls.
    stream_callback → function(chunk) for streaming output (Web UI only).
    """
    # Check if NVIDIA key exists
    if not os.getenv("NVIDIA_API_KEY"):
        log.debug("NVIDIA_API_KEY not set, using Groq fallback")
        return call_groq_fallback(messages, max_tokens=max_tokens, temperature=temperature)

    model = NVIDIA_FAST_MODEL if fast else NVIDIA_MAIN_MODEL
    try:
        # Use streaming if callback provided
        if stream_callback:
            resp = _get_nvidia().chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            full_text = ""
            for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    stream_callback(text)
            return full_text.strip()
        else:
            resp = _get_nvidia().chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"NVIDIA/Kimi failed ({e}), falling back to Groq 70B")
        return call_groq_fallback(messages, max_tokens=max_tokens, temperature=temperature)


def call_groq_fallback(messages: list, max_tokens=1200, temperature=0.7) -> str:
    """Final fallback - Groq 70B."""
    try:
        resp = _get_groq().chat.completions.create(
            model=GROQ_FALLBACK_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"All LLMs failed: {e}")
        return "I'm having trouble reaching my reasoning engine. Please try again."


def call_groq(messages: list, model=None, max_tokens=500, temperature=0.7) -> str:
    """Legacy compat — routes to NVIDIA/Kimi for prose, Groq for JSON routing."""
    last = messages[-1].get("content", "") if messages else ""
    is_json_call = "JSON" in last or "Return JSON" in last or max_tokens <= 250

    if is_json_call:
        return call_groq_router(messages, max_tokens=max_tokens)
    return call_nvidia(messages, max_tokens=max_tokens, temperature=temperature)


# ── Telegram helpers ──────────────────────────────────────────────

def send_telegram_alert(text: str):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        # Clean text for Telegram - remove problematic markdown chars
        clean = text[:4096]
        for char in ['_', '*', '[', ']', '(', ')', '`', '~', '>', '#', '+', '-', '=', '|', '{', '}']:
            clean = clean.replace(char, f'\\{char}')
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": clean, "parse_mode": "MarkdownV2"},
            timeout=5
        )
        if resp.status_code != 200:
            # Fallback: send without markdown
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4096]},
                timeout=5
            )
    except Exception as e:
        log.debug(f"Telegram send failed: {e}")
        # Last resort: plain text
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4096]},
                timeout=5
            )
        except:
            pass


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
        call_nvidia([{"role": "user", "content": "Say OK"}], max_tokens=10)
        status["nvidia"] = "OK"
        status["model"] = NVIDIA_MAIN_MODEL
    except Exception as e:
        status["nvidia"] = f"FAIL: {e}"

    return status


def call_nvidia_streaming(messages: list, max_tokens=1200, temperature=0.7):
    """Generator that yields text chunks for streaming."""
    import logging
    log = logging.getLogger("LLMGateway")
    
    if not os.getenv("NVIDIA_API_KEY"):
        yield call_groq_fallback(messages, max_tokens=max_tokens, temperature=temperature)
        return

    model = NVIDIA_MAIN_MODEL
    try:
        client = _get_nvidia()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        log.warning(f"NVIDIA streaming failed ({e}), using fallback")
        full = call_groq_fallback(messages, max_tokens=max_tokens, temperature=temperature)
        for i in range(0, len(full), 20):
            yield full[i:i+20]
