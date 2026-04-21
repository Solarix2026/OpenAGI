# Copyright (c) 2026 ApeironAI
# OpenAGI — An Apeiron Product
# MIT License

"""Quick validation for OpenAGI v5.7 (Prompt V5)."""
from pathlib import Path
import sys

checks = []

def check(name, fn):
    try:
        fn()
        checks.append(("✅", name))
    except Exception as e:
        checks.append(("❌", name, str(e)[:80]))

# Apeiron branding
check("Apeiron in kernel_impl", lambda: "Apeiron" in Path("core/kernel_impl.py").read_text(encoding="utf-8"))

# NL converter
check("NL converter importable", lambda: __import__('core.nl_to_structured', fromlist=['convert_to_structured']))

# Date normalization
check("Date normalization works", lambda: (
    __import__('core.nl_to_structured', fromlist=['normalize_date'])
    .normalize_date("next friday") != "next friday"
))

# Perplexity fallback
check("Perplexity RSS fallback works", lambda: (
    __import__('core.perplexity_client', fromlist=['get_breaking_news'])
    .get_breaking_news() is not None
))

# MCP server importable
check("MCP server importable", lambda: __import__('safety.mcp_server', fromlist=['build_mcp_manifest']))

# Print results
for c in checks:
    print(" ".join(str(x) for x in c))

fails = [c for c in checks if c[0] == "❌"]
print(f"\n{len(checks)-len(fails)}/{len(checks)} passed")
sys.exit(len(fails))
