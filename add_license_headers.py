# Copyright (c) 2026 HackerTMJ 
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""Add license headers to all Python files."""
from pathlib import Path

HEADER = '''# Copyright (c) 2026 HackerTMJ 
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

'''


def main():
    count = 0
    for py_file in Path('.').rglob('*.py'):
        path_str = str(py_file)
        # Skip venv, __pycache__, and already licensed files
        if 'venv' in path_str or '__pycache__' in path_str:
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
        except Exception:
            continue

        if 'Copyright' in content or 'License' in content[:200]:
            continue

        py_file.write_text(HEADER + content, encoding='utf-8')
        print(f'Header added: {py_file}')
        count += 1

    print(f'\nTotal: {count} files updated')


if __name__ == '__main__':
    main()
