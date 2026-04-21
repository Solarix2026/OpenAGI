# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""Safety package — Guard protocols and security"""
from .prompt_injection import PromptInjectionDetector

__all__ = ['PromptInjectionDetector']
