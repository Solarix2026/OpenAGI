# Copyright (c) 2026 ApeironAILab
# OpenAGI — An Apeiron Product
# MIT License
"""Direct line replacement."""

with open('core/tool_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 123 is index 122 (0-indexed)
print(f"Before: {repr(lines[122])}")

# Replace exactly " return reg" with "        return reg"
if lines[122].strip() == 'return reg':
    lines[122] = lines[122].replace('return reg', '        return reg').lstrip()
    print(f"After: {repr(lines[122])}")

# Also check if there's only one space
elif lines[122] == ' return reg\n' or lines[122] == ' return reg\r\n':
    lines[122] = '        return reg\n'
    print(f"Fixed: {repr(lines[122])}")

with open('core/tool_executor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Saved")
