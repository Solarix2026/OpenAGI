"""Safety package — Guard protocols and security"""
from .prompt_injection import PromptInjectionDetector

__all__ = ['PromptInjectionDetector']
