# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License
"""Check code blocks."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Count opening and closing patterns
parens = 0
brackets = 0
braces = 0

for i, line in enumerate(lines[:130], 1):
    # Skip comments and strings
    stripped = line.strip()

    # Count parens
    parens += line.count('(') - line.count(')')
    brackets += line.count('[') - line.count(']')
    braces += line.count('{') - line.count('}')

    if stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('return '):
        print(f"Line {i:3d}: parens={parens}, brackets={brackets}, braces={braces}, indent={len(line)-len(line.lstrip())}: {stripped[:50]}")

    if i == 123:
        print(f"\n--- Line 123 check ---")
        print(f"Parens: {parens}")
        print(f"Line content: {repr(line)}")
