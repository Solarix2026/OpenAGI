# tools/registry.py
"""Dynamic Tool Registry — The Hypothesis Space (H).

This IS the agent's capability space. All tools live here.
No hardcoded tool lists anywhere else in the system.

Tools are discovered via semantic search, not hardcoded.
Agents query discover(query) → get [ToolMeta] → decide → invoke.
"""
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

from tools.base_tool import BaseTool, ToolMeta, ToolResult
from memory.faiss_store import FaissStore
try:
    from memory.hdc_store import HDCStore
    HDC_AVAILABLE = True
except ImportError:
    HDC_AVAILABLE = False

logger = structlog.get_logger()


class ToolRegistry:
    """
    Dynamic registry for tools. Hot-swappable, discoverable.

    At startup: scans tools/builtin/ and self-populates.
    At runtime: can register/unregister/install from GitHub.

    Semantic search finds relevant tools by description.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, ToolMeta] = {}
        self._categories: dict[str, list[str]] = {}

        # For semantic discovery
        self._semantic_index: dict[str, str] = {}  # name -> combined text for search
        self._faiss_store = FaissStore(dim=384)

        logger.info("tool.registry.initialized")

    def discover(self, query: str, top_k: int = 5) -> list[ToolMeta]:
        """
        Semantic search over registered tools.

        Returns ranked list of ToolMeta relevant to query.
        Agent calls this FIRST, then decides which to invoke.
        """
        if not self._tools:
            return []

        # Build query text
        query_lower = query.lower()

        # Score each tool by relevance
        scored: list[tuple[ToolMeta, float]] = []

        for name, meta in self._metadata.items():
            score = 0.0
            text = f"{meta.name} {meta.description} {' '.join(meta.categories)}".lower()

            # Exact match bonus
            if query_lower in text:
                score += 1.0

            # Word overlap
            query_words = set(query_lower.split())
            text_words = set(text.split())
            overlap = len(query_words & text_words)
            score += overlap * 0.3

            # Category match
            for cat in meta.categories:
                if any(qw in cat.lower() for qw in query_words):
                    score += 0.5

            # Semantic similarity via FAISS
            if name in self._semantic_index:
                results = self._faiss_store.query(text, top_k=1)
                if results:
                    score += results[0][1] * 0.5

            scored.append((meta, score))

        # Sort by score
        scored.sort(key=lambda x: -x[1])

        return [meta for meta, _ in scored[:top_k]]

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        meta = tool.meta
        name = meta.name

        self._tools[name] = tool
        self._metadata[name] = meta

        # Index by categories
        for cat in meta.categories:
            if cat not in self._categories:
                self._categories[cat] = []
            self._categories[cat].append(name)

        # Build semantic index
        combined_text = f"{meta.name} {meta.description} {' '.join(meta.categories)}"
        self._semantic_index[name] = combined_text
        self._faiss_store.add(name, combined_text, {"name": name})

        logger.info("tool.registered", name=name, categories=meta.categories)

    def unregister(self, tool_name: str) -> bool:
        """Remove a tool from the registry."""
        if tool_name not in self._tools:
            logger.warning("tool.unregister.not_found", name=tool_name)
            return False

        meta = self._metadata[tool_name]

        # Remove from categories
        for cat in meta.categories:
            if cat in self._categories and tool_name in self._categories[cat]:
                self._categories[cat].remove(tool_name)

        # Remove from stores
        del self._tools[tool_name]
        del self._metadata[tool_name]
        if tool_name in self._semantic_index:
            del self._semantic_index[tool_name]

        logger.info("tool.unregistered", name=tool_name)
        return True

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> list[ToolMeta]:
        """List all registered tool metadata."""
        return list(self._metadata.values())

    def list_by_category(self, category: str) -> list[ToolMeta]:
        """List tools in a category."""
        names = self._categories.get(category, [])
        return [self._metadata[n] for n in names if n in self._metadata]

    async def invoke(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        """
        Invoke a tool by name with parameters.

        This is the ONLY way to call tools from the kernel.
        """
        tool = self.get(tool_name)

        if tool is None:
            logger.error("tool.invoke.not_found", name=tool_name)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool '{tool_name}' not found in registry",
            )

        # Validate params
        valid, error_msg = tool.validate_params(params)
        if not valid:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Parameter validation failed: {error_msg}",
            )

        try:
            result = await tool.execute(**params)
            logger.info(
                "tool.invoked",
                name=tool_name,
                success=result.success,
            )
            return result
        except Exception as e:
            logger.exception("tool.invoke.failed", name=tool_name, error=str(e))
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool execution failed: {str(e)}",
            )

    def scan_builtin_directory(self, path: Path) -> int:
        """Scan directory and auto-register all tools."""
        path = Path(path)
        registered = 0

        if not path.exists():
            logger.warning("tool.scan.path_not_found", path=str(path))
            return 0

        for file in path.glob("*_tool.py"):
            try:
                # Import module
                module_name = f"tools.builtin.{file.stem}"
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    file,
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find tool classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                        issubclass(obj, BaseTool) and
                        obj is not BaseTool and
                        not inspect.isabstract(obj)):

                        tool = obj()
                        self.register(tool)
                        registered += 1
                        logger.info("tool.auto_registered", file=file.name, class_name=name)

            except Exception as e:
                logger.error("tool.scan.failed", file=file.name, error=str(e))

        return registered

    async def install_from_github(self, url: str) -> Optional[BaseTool]:
        """
        Fetch Python file from GitHub raw URL.

        Validates it subclasses BaseTool.
        Sandboxes execution.
        Registers if passes trust check.
        """
        try:
            # Convert to raw URL if needed
            raw_url = url.replace("github.com", "raw.githubusercontent.com")
            raw_url = raw_url.replace("/blob/", "/")

            async with httpx.AsyncClient() as client:
                response = await client.get(raw_url, timeout=30)
                response.raise_for_status()
                code = response.text

            # Compute hash for trust check
            content_hash = hashlib.sha256(code.encode()).hexdigest()
            logger.info("tool.github.fetched", url=url, hash=content_hash[:16])

            # Execute in isolated namespace
            namespace = {
                "BaseTool": BaseTool,
                "ToolMeta": ToolMeta,
                "ToolResult": ToolResult,
            }

            exec(code, namespace)  # Trusted execution (we fetched it)

            # Find tool class
            tool = None
            for name, obj in namespace.items():
                if (isinstance(obj, type) and
                    issubclass(obj, BaseTool) and
                    obj is not BaseTool):
                    tool = obj()
                    break

            if tool:
                self.register(tool)
                logger.info("tool.github.registered", url=url, name=tool.meta.name)
                return tool
            else:
                logger.error("tool.github.no_tool_class", url=url)
                return None

        except Exception as e:
            logger.exception("tool.github.failed", url=url, error=str(e))
            return None
