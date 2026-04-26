# tests/tools/builtin/test_web_search_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.builtin.web_search_tool import WebSearchTool


@pytest.mark.asyncio
async def test_web_search_returns_results():
    tool = WebSearchTool()

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
    <a class="result__a" href="https://example.com/page1">Example Page 1</a>
    <a class="result__snippet">This is a snippet about the search result.</a>
    <a class="result__a" href="https://example.com/page2">Example Page 2</a>
    <a class="result__snippet">Another snippet here.</a>
    </body>
    </html>
    """

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(query="test query", max_results=2)

    assert result.success
    assert "results" in result.data
    assert len(result.data["results"]) >= 1
    assert result.data["results"][0]["title"] == "Example Page 1"
    assert result.data["results"][0]["url"] == "https://example.com/page1"


@pytest.mark.asyncio
async def test_web_search_handles_http_error():
    tool = WebSearchTool()

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Network error")

        result = await tool.execute(query="test query")

    assert not result.success
    assert "error" in result.error.lower() or "network" in result.error.lower()


@pytest.mark.asyncio
async def test_web_search_respects_max_results():
    tool = WebSearchTool()

    # Mock response with many results
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
    """ + "\n".join([f'<a class="result__a" href="https://example.com/page{i}">Page {i}</a>' for i in range(10)]) + """
    </body>
    </html>
    """

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(query="test query", max_results=3)

    assert result.success
    assert len(result.data["results"]) <= 3


@pytest.mark.asyncio
async def test_web_search_default_max_results():
    tool = WebSearchTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><a class='result__a' href='https://example.com'>Test</a></body></html>"

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(query="test query")

    assert result.success
    # Default max_results is 5


@pytest.mark.asyncio
async def test_web_search_tool_metadata():
    tool = WebSearchTool()
    assert tool.meta.name == "web_search"
    assert "query" in tool.meta.parameters["properties"]
    assert "max_results" in tool.meta.parameters["properties"]
    assert tool.meta.risk_score == 0.1
    assert "web" in tool.meta.categories
    assert "research" in tool.meta.categories


@pytest.mark.asyncio
async def test_web_search_empty_query():
    tool = WebSearchTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body></body></html>"

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(query="")

    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_web_search_includes_query_in_result():
    tool = WebSearchTool()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><a class='result__a' href='https://example.com'>Test</a></body></html>"

    with patch('tools.builtin.web_search_tool.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await tool.execute(query="python programming")

    assert result.success
    assert result.data["query"] == "python programming"
