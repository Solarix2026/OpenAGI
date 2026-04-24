# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License

"""Check tool_executor file structure."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find lines with specific content
for i, line in enumerate(lines):
    if 'def ' in line or 'return reg' in line:
        print(f"Line {i+1}: {line.strip()[:80]}")
