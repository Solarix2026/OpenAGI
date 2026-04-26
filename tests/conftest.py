# tests/conftest.py
"""Pytest configuration for OpenAGI v5 tests."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
