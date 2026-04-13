# Patch to add research tools
# Run this to patch tool_executor.py

import re

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the return reg line after take_screenshot
old_pattern = r'(reg\.register\("take_screenshot".*?\{\}\))'

new_code = r'''\1

        # Perplexity-style research tools
        reg.register("research_topic", self._research_topic,
            "Deep research on any topic: web search + synthesis + report",
            {"topic": {"type": "string", "required": True},
             "depth": {"type": "string", "default": "standard"}})

        reg.register("draft_document", self._draft_document,
            "Draft professional documents: RFC, report, memo based on research",
            {"document_type": {"type": "string", "required": True},
             "topic": {"type": "string", "required": True}})

        reg.register("investment_watchlist", self._investment_watchlist,
            "Get AI investment watchlist: stock analysis, trends, top picks",
            {"focus": {"type": "string", "default": "technology"}})'''

patched = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

with open('core/tool_executor.py', 'w', encoding='utf-8') as f:
    f.write(patched)

print("Patched!")
