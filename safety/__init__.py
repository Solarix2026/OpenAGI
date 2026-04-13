# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""Safety package — Guard protocols and security"""
from .prompt_injection import PromptInjectionDetector

__all__ = ['PromptInjectionDetector']
