# core/perplexity_client.py
"""Perplexity API for AI-powered news search with citations.

Free tier: 5 requests/min.
Model: sonar (fast news) or sonar-pro (deep research).
"""
import os, logging, requests

log = logging.getLogger("Perplexity")

BASE_URL = "https://api.perplexity.ai"


def search_news(query: str, focus: str = "news", max_tokens: int = 500) -> dict:
    """
    focus options: "news", "research", "finance", "general"
    Returns: {success, answer, citations, search_type}
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        # Fallback to RSS if no Perplexity key
        from core.worldmonitor_client import WorldMonitorClient
        wm = WorldMonitorClient()
        events = wm.get_events(limit=5)
        if events:
            result_text = "\n".join(f"• {e['title']}" for e in events[:5])
            return {"success": True, "answer": result_text, "citations": [], "source": "rss_fallback"}
        return {"success": False, "error": "No PERPLEXITY_API_KEY set and RSS fallback failed"}

    # Model selection based on focus
    model = "sonar" if focus == "news" else "sonar-pro"

    # Add recency hint
    system_msg = {
        "news": "Focus on the most recent news within the last 24-48 hours. Be concise.",
        "research": "Provide comprehensive analysis with multiple perspectives.",
        "finance": "Focus on financial news, market data, and economic implications.",
        "general": "Provide accurate, well-sourced information."
    }.get(focus, "Be concise and accurate.")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens,
        "return_citations": True,
        "search_recency_filter": "day" if focus == "news" else "week"
    }

    try:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        data = r.json()
        answer = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        return {
            "success": True,
            "answer": answer,
            "citations": citations[:5],
            "model": model,
            "source": "perplexity"
        }
    except Exception as e:
        log.error(f"Perplexity failed: {e}")
        return {"success": False, "error": str(e)}


def register_perplexity_tools(registry):
    def news_search(params: dict) -> dict:
        query = params.get("query", params.get("topic", ""))
        focus = params.get("focus", "news")
        if not query:
            return {"success": False, "error": "Provide query"}
        return search_news(query, focus)

    registry.register(
        "news_search",
        news_search,
        "Search for latest news using Perplexity AI (with citations). Falls back to RSS if no API key.",
        {
            "query": {"type": "string", "required": True},
            "focus": {"type": "string", "default": "news", "description": "news, research, finance, general"}
        },
        "research"
    )
