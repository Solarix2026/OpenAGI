# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License

"""Perplexity Sonar API — real-time news with citations."""
import os, logging, requests, json

log = logging.getLogger("Perplexity")
BASE = "https://api.perplexity.ai"
SONAR_MODEL = "sonar"
SONAR_PRO = "sonar-pro"

NEWS_TOPICS = {
    "finance": "stock market crypto finance latest news today",
    "ai": "artificial intelligence machine learning latest developments",
    "malaysia": "Malaysia technology business news latest",
    "geopolitics": "world politics geopolitics latest breaking news",
    "tech": "technology startup product launch latest",
}

def _call_perplexity(query: str, recency: str = "day", model: str = SONAR_MODEL, max_tokens: int = 500) -> dict:
    """Core Perplexity API call with citations."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Provide concise, factual news summary with key figures and context. Include date/time when known."},
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens,
        "return_citations": True,
        "search_recency_filter": recency,
        "temperature": 0.1,
    }
    try:
        r = requests.post(
            f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        data = r.json()
        return {
            "success": True,
            "answer": data["choices"][0]["message"]["content"],
            "citations": data.get("citations", [])[:5],
            "model": model,
            "source": "perplexity"
        }
    except Exception as e:
        log.warning(f"Perplexity API failed: {e}")
        return None

def get_breaking_news(topic: str = "technology finance ai") -> dict:
    """Get news from last hour — for real-time notifications."""
    result = _call_perplexity(
        f"Breaking news in the last 2 hours: {topic}",
        recency="hour",
        model=SONAR_MODEL,
        max_tokens=300
    )
    if result:
        return result
    # RSS fallback
    try:
        from core.worldmonitor_client import WorldMonitorClient
        wm = WorldMonitorClient()
        events = wm.get_events(limit=5)
        if events:
            summaries = "\n".join(f"• {e['title']}" for e in events[:5])
            return {"success": True, "answer": summaries, "citations": [], "source": "rss"}
    except Exception:
        pass
    return {"success": False, "error": "No news sources available"}

def search_news(query: str, focus: str = "news", deep: bool = False) -> dict:
    """General news search with topic focus."""
    recency_map = {"news": "day", "finance": "day", "research": "week", "general": "week"}
    recency = recency_map.get(focus, "day")
    model = SONAR_PRO if deep else SONAR_MODEL
    result = _call_perplexity(query, recency=recency, model=model, max_tokens=600)
    return result or {"success": False, "error": "Perplexity unavailable — no API key?"}

def register_perplexity_tools(registry):
    registry.register(
        "news_search",
        lambda p: search_news(p.get("query", ""), p.get("focus", "news"), p.get("deep", False)),
        "Search latest news (Perplexity Sonar + citations). focus: news/finance/research/general",
        {"query": {"type": "string", "required": True}, "focus": {"type": "string", "default": "news"}, "deep": {"type": "bool", "default": False}},
        "research"
    )
    registry.register(
        "breaking_news",
        lambda p: get_breaking_news(p.get("topic", "technology finance ai")),
        "Get breaking news from last 1-2 hours. Faster than news_search.",
        {"topic": {"type": "string", "default": "technology finance ai"}},
        "research"
    )
