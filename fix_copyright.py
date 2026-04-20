#!/usr/bin/env python
"""Fix copyright from Solarix2026 to ApeironAI."""
from pathlib import Path

OLD = "# Copyright (c) 2026 ApeironAI"
NEW = "# Copyright (c) 2026 ApeironAI"

changed = 0

for py_file in Path(".").rglob("*.py"):
    path_str = str(py_file)
    if ".backup" in path_str or "venv" in path_str or "__pycache__" in path_str or ".git" in path_str:
        continue

    try:
        content = py_file.read_text(encoding="utf-8")
        if OLD in content:
            py_file.write_text(content.replace(OLD, NEW), encoding="utf-8")
            changed += 1
            print(f"Updated: {py_file}")
    except Exception as e:
        print(f"Skip {py_file}: {e}")

print(f"\nFixed {changed} files")
