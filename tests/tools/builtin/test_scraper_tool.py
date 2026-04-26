# tests/tools/builtin/test_scraper_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.builtin.scraper_tool import ScraperTool


@pytest.mark.asyncio
async def test_scraper_fast_mode():
    tool = ScraperTool()

    # Mock httpx response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <head><title>Test Page</title></head>
    <body>
    <p>This is the main content of the page.</p>
    <p>More content here.</p>
    </body>
    </html>
    """

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com", mode="fast")

    assert result.success
    assert "content" in result.data
    assert "main content" in result.data["content"].lower()
    assert result.data["title"] == "Test Page"
    assert result.data["mode_used"] == "fast"


@pytest.mark.asyncio
async def test_scraper_auto_mode_selects_fast():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Auto Test</title></head><body>Content</body></html>"

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com", mode="auto")

    assert result.success
    assert result.data["mode_used"] == "fast"


@pytest.mark.asyncio
async def test_scraper_handles_http_error():
    tool = ScraperTool()

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection failed")

        result = await tool.execute(url="https://example.com")

    assert not result.success


@pytest.mark.asyncio
async def test_scraper_extracts_links():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
    <a href="https://example.com/page1">Link 1</a>
    <a href="https://example.com/page2">Link 2</a>
    </body>
    </html>
    """

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com", extract_links=True)

    assert result.success
    assert "links" in result.data
    assert len(result.data["links"]) >= 2


@pytest.mark.asyncio
async def test_scraper_word_count():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>This is a test with several words here.</body></html>"

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com")

    assert result.success
    assert "word_count" in result.data
    assert result.data["word_count"] > 0


@pytest.mark.asyncio
async def test_scraper_tool_metadata():
    tool = ScraperTool()
    assert tool.meta.name == "scraper"
    assert "url" in tool.meta.parameters["properties"]
    assert "mode" in tool.meta.parameters["properties"]
    assert "auto" in tool.meta.parameters["properties"]["mode"]["enum"]
    assert "fast" in tool.meta.parameters["properties"]["mode"]["enum"]
    assert "full" in tool.meta.parameters["properties"]["mode"]["enum"]
    assert tool.meta.risk_score == 0.15


@pytest.mark.asyncio
async def test_scraper_empty_page():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body></body></html>"

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com")

    assert result.success
    assert result.data["word_count"] == 0


@pytest.mark.asyncio
async def test_scraper_handles_redirects():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Redirected content</body></html>"

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com/redirect")

    assert result.success
    assert "redirected content" in result.data["content"].lower()


@pytest.mark.asyncio
async def test_scraper_includes_url_in_result():
    tool = ScraperTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Content</body></html>"

    with patch('tools.builtin.scraper_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(url="https://example.com/test")

    assert result.success
    assert result.data["url"] == "https://example.com/test"
