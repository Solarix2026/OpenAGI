#!/usr/bin/env python
"""Test web search directly."""

import asyncio
from ddgs import DDGS

async def test_web_search():
    """Test web search directly."""
    print("Testing web search...")

    try:
        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text("AI news 2026", max_results=5)
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "body": result.get("body", "")
                })

        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\n{i+1}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Body: {result['body'][:100]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_web_search())
