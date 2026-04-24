# Copyright (c) 2026 ApeironAILab
# OpenAGI - Autonomous Intelligence System
# MIT License

"""Dynamic loader for agency-agents specialist prompts."""

import json
import logging
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("AgencyLoader")

CACHE_DIR = Path("./workspace/agency_cache")
CACHE_TTL_DAYS = 7
RAW_BASE = "https://raw.githubusercontent.com/msitarzewski/agency-agents/main"
API_BASE = "https://api.github.com/repos/msitarzewski/agency-agents/contents"
DIVISIONS = {
    "engineering": "engineering", "design": "design", "marketing": "marketing", "product": "product",
    "support": "support", "operations": "operations", "research": "research", "spatial": "spatial-computing",
    "qa": "quality-assurance", "security": "security", "data": "data", "strategy": "strategy",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9._-]", "-", (text or "").lower().strip())


def _cache_path(agent_name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_slug(agent_name)}.md"


def _index_path() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "_index.json"


def _is_fresh(path: Path) -> bool:
    return path.exists() and (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)) < timedelta(days=CACHE_TTL_DAYS)


def _fetch(url: str, timeout: int = 10, headers: dict | None = None, as_json: bool = False):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if as_json else raw
    except Exception:
        return None


def list_available_agents() -> dict:
    """List cached agents and refresh index from GitHub when stale."""
    idx = _index_path()
    if _is_fresh(idx):
        try:
            return json.loads(idx.read_text(encoding="utf-8"))
        except Exception:
            pass

    agents = {}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for md in CACHE_DIR.glob("*.md"):
        if md.stem.startswith("_"):
            continue
        content = md.read_text(encoding="utf-8", errors="replace")
        name = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
        desc = re.search(r"^description:\s*(.+)$", content, re.MULTILINE)
        div = re.search(r"^division:\s*(.+)$", content, re.MULTILINE)
        agents[md.stem] = {
            "name": name.group(1).strip() if name else md.stem,
            "description": desc.group(1).strip() if desc else "",
            "division": div.group(1).strip() if div else "general",
            "source": "cache",
        }

    headers = {"User-Agent": "OpenAGI/5.8"}
    for division, repo_path in DIVISIONS.items():
        rows = _fetch(f"{API_BASE}/{repo_path}", timeout=15, headers=headers, as_json=True)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name", "")
            if not name.endswith(".md"):
                continue
            slug = name[:-3]
            base = agents.get(slug, {})
            agents[slug] = {
                "name": base.get("name", slug),
                "description": base.get("description", ""),
                "division": base.get("division", division),
                "download_url": row.get("download_url", ""),
                "source": "cache+github" if base else "github",
            }

    try:
        idx.write_text(json.dumps(agents, indent=2), encoding="utf-8")
    except Exception as e:
        log.debug("Index write failed: %s", e)
    return agents


def fetch_agent(agent_name: str, division: str = "") -> str | None:
    """Fetch agent markdown from cache or GitHub."""
    slug = _slug(agent_name)
    if not slug:
        return None

    cache = _cache_path(slug)
    if _is_fresh(cache):
        return cache.read_text(encoding="utf-8", errors="replace")

    search_paths = []
    if division:
        search_paths.append(DIVISIONS.get(division.lower(), division))
    search_paths.extend(DIVISIONS.values())

    seen = set()
    for div in search_paths:
        if div in seen:
            continue
        seen.add(div)
        content = _fetch(f"{RAW_BASE}/{div}/{slug}.md", timeout=8)
        if content:
            cache.write_text(content, encoding="utf-8")
            log.info("[AGENCY] Downloaded %s from %s", slug, div)
            return content

    direct = list_available_agents().get(slug, {}).get("download_url", "")
    if direct:
        content = _fetch(direct, timeout=8)
        if content:
            cache.write_text(content, encoding="utf-8")
            return content

    log.debug("[AGENCY] Not found: %s", slug)
    return None


def find_best_agent(task: str, available: dict) -> tuple[str, float]:
    """Suggest best agent by keyword overlap. LLM makes final decision."""
    task_words = set(re.findall(r"\w{4,}", (task or "").lower()))
    if not task_words:
        return "", 0.0

    best_name, best_score = "", 0.0
    for name, info in available.items():
        desc = (info.get("description", "") + " " + name).lower()
        desc_words = set(re.findall(r"\w{4,}", desc))
        score = len(task_words & desc_words) / max(len(task_words), 1)
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


def extract_system_prompt(agent_md: str) -> str:
    """Strip YAML frontmatter and return clean system prompt text."""
    content = agent_md or ""
    if content.startswith("---"):
        content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    return content.strip()[:6000]


def register_agency_tools(registry, executor):
    """Register dynamic agency tools with ToolRegistry."""

    def activate_agent(params: dict) -> dict:
        agent = (params.get("agent") or params.get("role") or "").strip().lower().replace(" ", "-")
        task = params.get("task", "")
        context = params.get("context", "")
        if not agent:
            available = list_available_agents()
            agent, confidence = find_best_agent(task, available)
            if confidence < 0.2:
                return {
                    "success": False,
                    "error": f"No suitable specialist found for: {task[:80]}",
                    "hint": "Use list_agency_agents to inspect available specialists.",
                }

        agent_md = fetch_agent(agent)
        if not agent_md:
            return {"success": False, "error": f"Agent '{agent}' not found in agency-agents"}

        system_prompt = extract_system_prompt(agent_md)
        if task:
            from core.llm_gateway import call_nvidia

            prompt = task + (f"\n\nContext: {context}" if context else "")
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            result = call_nvidia(messages, max_tokens=1500)
            return {
                "success": True,
                "agent": agent,
                "result": result,
                "data": result,
                "agent_loaded_from": "github.com/msitarzewski/agency-agents",
            }

        return {
            "success": True,
            "agent": agent,
            "system_prompt_preview": system_prompt[:300],
            "message": f"Agent '{agent}' loaded. Provide a task to activate.",
        }

    def list_agency_agents(params: dict) -> dict:
        division = (params.get("division") or "").strip().lower()
        available = list_available_agents()
        if division:
            available = {k: v for k, v in available.items() if v.get("division", "").lower() == division}
        return {
            "success": True,
            "count": len(available),
            "agents": available,
            "source": "github.com/msitarzewski/agency-agents",
        }

    def download_division(params: dict) -> dict:
        division = (params.get("division") or "engineering").strip().lower()
        path = DIVISIONS.get(division, division)
        rows = _fetch(f"{API_BASE}/{path}", timeout=15, headers={"User-Agent": "OpenAGI/5.8"}, as_json=True)
        if not isinstance(rows, list):
            return {"success": False, "error": f"Unable to list division '{division}'"}

        downloaded = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name, url = row.get("name", ""), row.get("download_url", "")
            if not name.endswith(".md") or not url:
                continue
            content = _fetch(url, timeout=8)
            if not content:
                continue
            slug = name[:-3]
            _cache_path(slug).write_text(content, encoding="utf-8")
            downloaded.append(slug)

        _ = list_available_agents()
        return {"success": True, "division": division, "downloaded": downloaded, "count": len(downloaded)}

    registry.register(
        "activate_agent", activate_agent,
        "Activate a specialist AI agent from agency-agents by name or task description.",
        {"agent": {"type": "string", "optional": True}, "task": {"type": "string", "required": True}, "context": {"type": "string", "optional": True}},
        "organization",
    )
    registry.register(
        "list_agency_agents", list_agency_agents,
        "List available specialist agents from agency-agents.",
        {"division": {"type": "string", "optional": True}},
        "organization",
    )
    registry.register(
        "download_agent_division", download_division,
        "Bulk download all specialist agents from a division for offline use.",
        {"division": {"type": "string", "required": True}},
        "organization",
    )
