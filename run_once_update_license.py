#!/usr/bin/env python
"""One-time script to update copyright headers in all Python files."""
from pathlib import Path
import sys

OLD = "# Copyright (c) 2026 Solarix2026"
NEW = "# Copyright (c) 2026 Solarix2026"

changed = 0
default_encoding = sys.getdefaultencoding()

print("Scanning for files to update...")
print(f"Looking for: {OLD}")
print(f"Replacing with: {NEW}")
print()

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

print(f"\n{'='*50}")
print(f"✅ Updated {changed} files")
print(f"{'='*50}")
print("\nYou can now delete this script if all files were updated correctly.")
