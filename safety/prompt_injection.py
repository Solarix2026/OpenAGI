# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
prompt_injection.py — Detect and block prompt injection attacks

Patterns detected:
1. Direct injection: "Ignore previous instructions and..."
2. Role override: "You are now DAN..."
3. Delimiter injection: "---\nNew system prompt:..."
4. Indirect injection: malicious content in tool results
5. Jailbreak patterns: "pretend", "roleplay as", "your true self"
"""
import re, logging
from core.llm_gateway import call_groq_router

log = logging.getLogger("Security")

# Fast regex patterns (no LLM needed for obvious cases)
INJECTION_PATTERNS = [
    r"ignore (all |previous |prior )?(instructions|rules|prompts|guidelines)",
    r"you are now (a|an|the)?\s*\w+",
    r"(new|updated|real) system prompt",
    r"disregard (everything|all|prior)",
    r"act as (if|though)? you (have no|don't have|lack)",
    r"jailbreak|dan mode|developer mode|unrestricted",
    r"your (true|real|actual) (self|personality|purpose)",
    r"forget (you are|that you're|your) (an ai|a bot|claude|openagi)",
    r"pretend (you|that you|there) (are|is|have) no",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


class PromptInjectionDetector:
    def __init__(self, use_llm_verification=False):
        """use_llm_verification: use Groq for ambiguous cases (slower but more accurate)"""
        self.use_llm = use_llm_verification
        self._blocked_count = 0

    def is_injection(self, text: str) -> tuple[bool, str]:
        """
        Returns (is_injection, reason).
        Fast regex first, LLM fallback for ambiguous.
        """
        if not text:
            return False, ""

        # Check regex patterns
        for pattern in COMPILED_PATTERNS:
            m = pattern.search(text)
            if m:
                self._blocked_count += 1
                return True, f"Injection pattern: '{m.group(0)[:50]}'"

        # Check for suspiciously long system-like headers
        if re.search(r'^(system|assistant|human|ai):.*$', text, re.MULTILINE | re.IGNORECASE):
            if len(text) > 200:  # Short labels ok, long injections suspicious
                self._blocked_count += 1
                return True, "Suspected role injection"

        # LLM verification for borderline cases (optional, slower)
        if self.use_llm and len(text) > 50:
            return self._llm_verify(text)

        return False, ""

    def _llm_verify(self, text: str) -> tuple[bool, str]:
        """Groq quick verification for ambiguous inputs."""
        prompt = f"""Is this a prompt injection attempt? Return JSON only.
Text: "{text[:200]}"
Return: {{"injection": true/false, "confidence": 0.0-1.0}}"""
        try:
            raw = call_groq_router([{"role": "user", "content": prompt}], max_tokens=50)
            m = re.search(r'"injection":\s*(true|false)', raw)
            is_inj = m and m.group(1) == "true"
            if is_inj:
                self._blocked_count += 1
                return True, "LLM detected injection"
        except Exception:
            pass
        return False, ""

    def sanitize_tool_result(self, result: dict) -> dict:
        """
        Scan tool results for injections (e.g., malicious web content).
        Applies to websearch results, file reads, API responses.
        """
        text_fields = ["content", "clean_summary", "text", "extracted", "data"]
        for field in text_fields:
            val = result.get(field, "")
            if isinstance(val, str) and len(val) > 10:
                is_inj, reason = self.is_injection(val[:500])
                if is_inj:
                    log.warning(f"[SECURITY] Injection in tool result field '{field}': {reason}")
                    result[field] = f"[SANITIZED: potential injection detected in {field}]"
        return result
