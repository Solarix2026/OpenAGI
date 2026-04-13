# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
video_deck_skill.py — Generate video presentation decks

generate_deck(topic, style, slides=10) → websearch → NVIDIA outline →
save MD + HTML → return {path_md, path_html, slide_count}

HTML uses dark presentation style, keyboard-navigable.
register_as_tool: "video_deck" tool.
"""
import logging
from pathlib import Path
from core.llm_gateway import call_nvidia

log = logging.getLogger("VideoDeck")
DECKS_DIR = Path("./workspace/decks")


class VideoDeckSkill:
    def __init__(self, executor):
        self.executor = executor
        DECKS_DIR.mkdir(parents=True, exist_ok=True)

    def generate_deck(self, topic: str, style: str = "professional", slides: int = 10) -> dict:
        """
        Generate a presentation deck on a topic.
        Returns paths to markdown and HTML versions.
        """
        # Step 1: Research
        from core.tool_executor import ToolExecutor
        search_result = self.executor.execute({
            "action": "websearch",
            "parameters": {"query": f"{topic} latest trends developments"}
        })
        research = search_result.get("data", {}).get("clean_summary", "") if search_result.get("success") else ""

        # Step 2: Generate outline with NVIDIA
        prompt = f"""Create a {slides}-slide presentation outline for: "{topic}"

Style: {style}
Research: {research[:500]}

For each slide provide:
- Title
- 2-3 bullet points
- Optional speaker notes

Return as JSON: {{"slides": [{{"title": "...", "bullets": ["..."], "notes": "..."}}]}}"""

        raw = call_nvidia([{"role": "user", "content": prompt}], max_tokens=1000)
        import json, re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        deck_data = json.loads(m.group(0)) if m else {"slides": []}
        slide_list = deck_data.get("slides", [])

        # Step 3: Generate Markdown
        safe_name = topic.lower().replace(" ", "_").replace("/", "_")[:30]
        md_path = DECKS_DIR / f"{safe_name}.md"
        html_path = DECKS_DIR / f"{safe_name}.html"

        md_content = f"# {topic}\n\n*{style} presentation*\n\n"
        for i, slide in enumerate(slide_list, 1):
            md_content += f"## Slide {i}: {slide.get('title', '')}\n\n"
            for bullet in slide.get('bullets', []):
                md_content += f"- {bullet}\n"
            if slide.get('notes'):
                md_content += f"\n_Notes: {slide['notes']}_\n"
            md_content += "\n---\n\n"
        md_path.write_text(md_content, encoding="utf-8")

        # Step 4: Generate HTML (dark theme, keyboard-navigable)
        html_content = self._generate_html_deck(topic, slide_list, style)
        html_path.write_text(html_content, encoding="utf-8")

        log.info(f"[DECK] Generated: {topic} ({len(slide_list)} slides)")
        return {
            "success": True,
            "topic": topic,
            "slides": len(slide_list),
            "path_md": str(md_path),
            "path_html": str(html_path)
        }

    def _generate_html_deck(self, title: str, slides: list, style: str) -> str:
        """Generate dark-themed HTML presentation."""
        slides_html = ""
        for i, slide in enumerate(slides):
            bullets = "".join([f'<li class="mb-2">{b}</li>' for b in slide.get('bullets', [])])
            notes = f'<div class="text-gray-500 text-sm mt-4">{slide.get("notes", "")}</div>' if slide.get('notes') else ""
            slides_html += f'''
            <div class="slide" id="slide-{i}">
                <h2 class="text-3xl font-bold text-white mb-6">{slide.get('title', '')}</h2>
                <ul class="text-xl text-gray-300">{bullets}</ul>
                {notes}
                <div class="absolute bottom-8 right-8 text-gray-600">{i+1}/{len(slides)}</div>
            </div>
            '''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ background: #0a0a0a; font-family: 'Inter', sans-serif; overflow: hidden; }}
        .slide {{ display: none; width: 100vw; height: 100vh; padding: 4rem; position: relative; }}
        .slide.active {{ display: flex; flex-direction: column; justify-content: center; }}
        .nav-hint {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    {slides_html}
    <div class="nav-hint">← → or Space to navigate</div>
    <script>
        let current = 0;
        const slides = document.querySelectorAll('.slide');
        slides[0].classList.add('active');
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') {{
                slides[current].classList.remove('active');
                current = Math.min(current + 1, slides.length - 1);
                slides[current].classList.add('active');
            }} else if (e.key === 'ArrowLeft') {{
                slides[current].classList.remove('active');
                current = Math.max(current - 1, 0);
                slides[current].classList.add('active');
            }}
        }});
    </script>
</body>
</html>'''

    def register_as_tool(self, registry):
        skill = self

        def video_deck(params: dict) -> dict:
            topic = params.get("topic", "")
            style = params.get("style", "professional")
            slides = int(params.get("slides", 10))
            if not topic:
                return {"success": False, "error": "Topic required"}
            return skill.generate_deck(topic, style, slides)

        registry.register(
            name="video_deck",
            func=video_deck,
            description="Generate a video presentation deck on any topic with customizable style and slide count",
            parameters={
                "topic": {"type": "string", "required": True},
                "style": {"type": "string", "default": "professional"},
                "slides": {"type": "integer", "default": 10}
            },
            category="generation"
        )
