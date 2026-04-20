""" arXiv API — free, no key. Search academic papers. """
import requests, logging
from xml.etree import ElementTree as ET

log = logging.getLogger("arXiv")


def search_papers(query: str, max_results: int = 5) -> dict:
    try:
        r = requests.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            },
            timeout=15
        )
        root = ET.fromstring(r.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []
        for entry in root.findall("atom:entry", ns):
            papers.append({
                "title": entry.findtext("atom:title", "", ns).strip(),
                "summary": entry.findtext("atom:summary", "", ns).strip()[:300],
                "authors": [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)][:3],
                "published": entry.findtext("atom:published", "", ns)[:10],
                "url": entry.findtext("atom:id", "", ns),
            })
        return {"success": True, "papers": papers, "query": query, "source": "arXiv"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_arxiv_tool(registry):
    def arxiv_search(params: dict) -> dict:
        return search_papers(params.get("query", ""), int(params.get("max_results", 5)))

    registry.register(
        "arxiv_search",
        arxiv_search,
        "Search arXiv for academic papers on any topic: AI, physics, mathematics, biology, etc. Free, no API key.",
        {"query": {"type": "string", "required": True}, "max_results": {"type": "integer", "default": 5}},
        "research"
    )
