# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
OpenAGI Kernel Entry Point
Thin wrapper that imports from the core package.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main kernel
from core.kernel_impl import Kernel

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    kernel = Kernel()

    if mode == "voice":
        kernel.run_voice_mode()
    elif mode == "web":
        kernel.run_web()
    elif mode == "cli":
        kernel.run_cli()
    elif mode == "telegram" or os.getenv("TELEGRAM_BOT_TOKEN"):
        kernel.run_telegram()
    else:
        kernel.run_cli()
