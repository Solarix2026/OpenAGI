# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
plugin_api.py — Plugin management system

Plugin = Python file in ./plugins/ with PLUGIN_META dict + run() function.
load_all() → import all plugins, register their tools.
install(url) → download + safety check + load.
list_plugins() → return metadata list.
"""
import logging
import sys
import importlib.util
from pathlib import Path
import requests
import re

log = logging.getLogger("Plugins")
PLUGINS_DIR = Path("./plugins")


class PluginManager:
    def __init__(self, registry):
        self.registry = registry
        self._plugins: dict[str, dict] = {}
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    def load_all(self):
        """Load all plugins from plugins directory."""
        for py_file in PLUGINS_DIR.glob("*.py"):
            try:
                self._load_plugin(py_file)
            except Exception as e:
                log.warning(f"Failed to load plugin {py_file}: {e}")

    def _load_plugin(self, path: Path) -> dict:
        """Load a single plugin file."""
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)

        # Trap dangerous imports
        orig_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __builtins__['__import__']

        def safe_import(name, *args, **kwargs):
            dangerous = ['os.system', 'subprocess.call', 'eval', 'exec', '__import__']
            if any(d in name for d in dangerous):
                raise ImportError(f"Plugin blocked import: {name}")
            return orig_import(name, *args, **kwargs)

        try:
            if hasattr(__builtins__, '__import__'):
                __builtins__.__import__ = safe_import
            else:
                __builtins__['__import__'] = safe_import
        except:
            pass

        spec.loader.exec_module(module)
        meta = getattr(module, "PLUGIN_META", {})
        run = getattr(module, "run", None)

        if not meta.get("name") or not run:
            raise ValueError("Plugin missing PLUGIN_META or run function")

        # Register tools
        tools = meta.get("tools", [])
        for tool in tools:
            self.registry.register(
                name=tool.get("name", path.stem),
                func=lambda p, r=run, t=tool: self._wrap_plugin(r, t, p),
                description=tool.get("description", meta.get("description", "Plugin function")),
                parameters=tool.get("parameters", {}),
                category=meta.get("category", "plugin")
            )

        plugin_info = {
            "name": meta["name"],
            "version": meta.get("version", "0.1"),
            "description": meta.get("description", ""),
            "path": str(path),
            "tools": [t["name"] for t in tools]
        }
        self._plugins[meta["name"]] = plugin_info
        log.info(f"[PLUGIN] Loaded: {meta['name']}")
        return plugin_info

    def _wrap_plugin(self, run_func, tool_spec, params: dict):
        """Wrap a plugin run function with proper error handling."""
        try:
            return run_func(tool_spec.get("name", ""), params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def install(self, url: str) -> dict:
        """Download and install a plugin from URL."""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            filename = parsed.path.split("/")[-1] or "plugin.py"

            # Download
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            code = resp.text

            # Safety check
            dangerous_patterns = [
                r'os\.system', r'subprocess\.call', r'subprocess\.run',
                r'eval\(', r'exec\(', r'__import__',
                r'import\s+os\s*;\s*os\.system'
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return {"success": False, "error": f"Safety check failed: {pattern}"}

            # Save
            plugin_path = PLUGINS_DIR / filename
            plugin_path.write_text(code)

            # Load
            info = self._load_plugin(plugin_path)
            return {"success": True, "plugin": info}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def uninstall(self, name: str) -> bool:
        """Remove a plugin."""
        if name not in self._plugins:
            return False
        plugin = self._plugins.pop(name)
        path = Path(plugin["path"])
        if path.exists():
            path.unlink()
        log.info(f"[PLUGIN] Uninstalled: {name}")
        return True

    def list_plugins(self) -> list:
        """List all loaded plugins."""
        return list(self._plugins.values())

    def get_plugin(self, name: str) -> dict | None:
        """Get plugin info by name."""
        return self._plugins.get(name)
