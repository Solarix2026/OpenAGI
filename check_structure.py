# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License
"""Check file structure."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check indentation of function definitions and returns
indent_stack = []
for i, line in enumerate(lines[:150], 1):
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    if stripped.startswith('def ') or stripped.startswith('class '):
        print(f"Line {i}: {indent} spaces - {stripped[:50]}")
        indent_stack.append((i, indent))
    elif stripped.startswith('return ') and indent < 8:
        print(f"Line {i}: PROBLEM - return at {indent} spaces: {repr(stripped[:30])}")
    elif 'return' in stripped and i > 100 and i < 130:
        print(f"Line {i}: {indent} spaces - return in context")
