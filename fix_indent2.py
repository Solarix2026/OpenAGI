# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License
"""Fix indentation issue."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# Find line with return reg
for i, line in enumerate(lines):
    if 'return reg' in line:
        print(f"Line {i+1}: bytes={[hex(ord(c)) for c in line[:20]]}")
        print(f"   content: {repr(line)}")
        print(f"   starts with space: {line.startswith(' ')}")
        print(f"   strip: {repr(line.strip())}")

# Fix the specific line (123)
if len(lines) >= 123:
    line123 = lines[122]  # 0-indexed
    if line123.strip() == 'return reg':
        lines[122] = '        return reg'
        print("\nFixed line 123")

content = '\n'.join(lines)
with open('core/tool_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
