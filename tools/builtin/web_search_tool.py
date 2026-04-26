# tools/builtin/web_search_tool.py
"""Web search tool using DuckDuckGo.

Performs web searches and returns results.
"""
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class WebSearchTool(BaseTool):
    """
    Search the web using DuckDuckGo.

    - Returns search results
    - No API key required
    - Privacy-focused
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="web_search",
            description="Search the web using DuckDuckGo",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            risk_score=0.3,
            categories=["web", "search"],
            examples=[
                {
                    "query": "Python async programming",
                    "max_results": 5
                }
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Perform web search."""
        import time
        start_time = time.time()

        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 10)

        if not query:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No query provided"
            )

        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                search_results = ddgs.text(query, max_results=max_results)
                for result in search_results:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "body": result.get("body", "")
                    })

            return ToolResult(
                success=True,
                tool_name=self.meta.name,
                data=results,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={"query": query, "count": len(results)}
            )

        except ImportError:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="duckduckgo-search package not installed. Install with: pip install duckduckgo-search"
            )
        except Exception as e:
            logger.exception("web_search.tool.error", query=query, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Web search failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
