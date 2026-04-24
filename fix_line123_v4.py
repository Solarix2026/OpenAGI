# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License
"""Fix line 123 with proper indentation."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 123 is index 122
print(f"Before: {repr(lines[122])}")

# Set it to exactly 8 spaces + return reg + newline
lines[122] = '        return reg\n'
print(f"After: {repr(lines[122])}")

with open('core/tool_executor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Saved successfully")
