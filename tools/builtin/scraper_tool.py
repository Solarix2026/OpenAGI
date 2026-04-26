# tools/builtin/scraper_tool.py
"""Web scraping tool using trafilatura and playwright.

Extracts content from web pages.
"""
from typing import Any

import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult

logger = structlog.get_logger()


class ScraperTool(BaseTool):
    """
    Scrape web pages for content.

    - Uses trafilatura for text extraction
    - Uses playwright for JavaScript rendering
    - Returns clean, structured content
    """

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="scraper",
            description="Extract content from web pages using trafilatura and playwright",
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape"
                    },
                    "use_playwright": {
                        "type": "boolean",
                        "description": "Use playwright for JavaScript rendering (default: false)",
                        "default": False
                    }
                },
                "required": ["url"]
            },
            risk_score=0.4,
            categories=["web", "scraping"],
            examples=[
                {
                    "url": "https://example.com",
                    "use_playwright": False
                }
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Scrape web page content."""
        import time
        start_time = time.time()

        url = kwargs.get("url", "")
        use_playwright = kwargs.get("use_playwright", False)

        if not url:
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error="No URL provided"
            )

        try:
            if use_playwright:
                # Use playwright for JavaScript rendering
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()
                    await page.goto(url)
                    content = await page.content()
                    await browser.close()

                # Extract text from HTML
                from trafilatura import extract
                extracted = extract(content)

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=extracted or content,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"url": url, "method": "playwright"}
                )
            else:
                # Use trafilatura directly (faster, no JS)
                import trafilatura

                downloaded = trafilatura.fetch_url(url)
                if downloaded is None:
                    return ToolResult(
                        success=False,
                        tool_name=self.meta.name,
                        error=f"Failed to fetch URL: {url}"
                    )

                extracted = trafilatura.extract(downloaded)

                return ToolResult(
                    success=True,
                    tool_name=self.meta.name,
                    data=extracted or downloaded,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"url": url, "method": "trafilatura"}
                )

        except ImportError as e:
            missing_pkg = str(e).split("'")[1] if "'" in str(e) else "required package"
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Package not installed: {missing_pkg}. Install with: pip install trafilatura playwright"
            )
        except Exception as e:
            logger.exception("scraper.tool.error", url=url, error=str(e))
            return ToolResult(
                success=False,
                tool_name=self.meta.name,
                error=f"Scraping failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
