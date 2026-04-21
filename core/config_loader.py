# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
config_loader.py — Configuration management for OpenAGI

Loads declarative patterns, LLM thresholds, and other configurable behaviors.
"""
import yaml
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

log = logging.getLogger("ConfigLoader")

CONFIG_DIR = Path("./config")


class ConfigLoader:
    """Manages declarative pattern detection with pattern + LLM hybrid."""

    def __init__(self):
        self.patterns: List[Dict[str, Any]] = []
        self.categories: List[str] = []
        self.llm_threshold: float = 0.7
        self.strategy: str = "hybrid"
        self._load_declarative_config()

    def _load_declarative_config(self):
        """Load declarative pattern config from YAML."""
        config_path = CONFIG_DIR / "declarative_patterns.yaml"

        if not config_path.exists():
            log.warning("Declarative config not found, using defaults")
            self._use_default_patterns()
            return

        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

            self.patterns = config.get("patterns", [])
            self.categories = config.get("categories", ["name", "job", "location"])
            self.llm_threshold = config.get("llm_confidence_threshold", 0.7)
            self.strategy = config.get("extraction_strategy", "hybrid")

            log.info(f"Loaded {len(self.patterns)} declarative patterns, strategy: {self.strategy}")
        except Exception as e:
            log.error(f"Failed to load declarative config: {e}")
            self._use_default_patterns()

    def _use_default_patterns(self):
        """Fallback patterns if config file missing."""
        self.patterns = [
            {"pattern": "my name is", "type": "name", "priority": 1.0, "extract_regex": None},
            {"pattern": "i am ", "type": "identity", "priority": 0.8, "extract_regex": None},
            {"pattern": "i work ", "type": "job", "priority": 0.9, "extract_regex": None},
            {"pattern": "i live ", "type": "location", "priority": 0.9, "extract_regex": None},
            {"pattern": "call me ", "type": "name", "priority": 1.0, "extract_regex": None},
            {"pattern": "我叫", "type": "name", "priority": 1.0, "extract_regex": None},
            {"pattern": "我是", "type": "identity", "priority": 0.8, "extract_regex": None},
            {"pattern": "我在", "type": "location", "priority": 0.8, "extract_regex": None},
        ]
        self.categories = ["name", "job", "location", "preference"]
        self.strategy = "hybrid"

    def is_declarative(self, text: str) -> tuple[bool, Optional[str], float]:
        """
        Check if input is declarative using pattern matching.
        Returns: (is_declarative, detected_type, confidence)
        """
        text_lower = text.lower()

        for p in self.patterns:
            pattern_str = p.get("pattern", "")
            if pattern_str in text_lower:
                return True, p.get("type"), p.get("priority", 0.8)

        return False, None, 0.0

    def extract_with_regex(self, text: str, fact_type: str) -> Optional[Dict[str, str]]:
        """Extract fact using configured regex patterns."""
        for p in self.patterns:
            if p.get("type") != fact_type:
                continue

            regex = p.get("extract_regex")
            if not regex:
                continue

            try:
                m = re.search(regex, text, re.I)
                if m:
                    return {"type": fact_type, "value": m.group(1).strip(), "method": "regex"}
            except Exception as e:
                log.debug(f"Regex extraction failed: {e}")
                continue

        return None

    def should_use_llm_extraction(self, text: str, pattern_matched: bool) -> bool:
        """Determine if LLM extraction should be used."""
        if self.strategy == "pattern_only":
            return False
        if self.strategy == "llm_only":
            return True
        # hybrid: use LLM if pattern didn't match, or as secondary validation
        return not pattern_matched or True  # Always run LLM in hybrid for better quality

    def llm_extract_personal_facts(self, text: str, call_nvidia_func) -> List[Dict[str, str]]:
        """
        Use LLM to extract personal facts from text.
        Returns list of extracted facts.
        """
        prompt = f"""Extract personal facts from this user input.

User input: "{text}"

Analyze if this contains declarations of:
- User's name (e.g., "my name is...", "我叫...", "call me...")
- User's job/profession (e.g., "I work as...", "I am a...")
- User's location (e.g., "I live in...", "I'm from...")
- User's preferences (e.g., "I like...", "I prefer...")

Return ONLY valid JSON:
{{
  "contains_facts": true/false,
  "facts": [
    {{
      "type": "name|job|location|preference|relationship",
      "value": "extracted value",
      "confidence": 0.0-1.0
    }}
  ],
  "confidence": 0.0-1.0
}}

Be strict: only return facts if clearly stated in the input."""

        try:
            response = call_nvidia_func(
                [{"role": "user", "content": prompt}],
                max_tokens=300,
                fast=True
            )

            # Extract JSON
            m = re.search(r'\{.*\}', response, re.DOTALL)
            if not m:
                return []

            data = json.loads(m.group(0))

            if not data.get("contains_facts"):
                return []

            confidence = data.get("confidence", 0.0)
            if confidence < self.llm_threshold:
                log.debug(f"LLM confidence {confidence} below threshold {self.llm_threshold}")
                return []

            facts = data.get("facts", [])
            return [f for f in facts if f.get("confidence", 0) >= self.llm_threshold]

        except Exception as e:
            log.debug(f"LLM extraction failed: {e}")
            return []

    def extract_facts(self, text: str, call_nvidia_func=None) -> List[Dict[str, str]]:
        """
        Master extraction method: pattern + LLM hybrid.
        Returns list of extracted facts with metadata.
        """
        facts = []

        # Step 1: Pattern matching
        is_declarative, fact_type, confidence = self.is_declarative(text)

        if is_declarative:
            # Try regex extraction first
            regex_fact = self.extract_with_regex(text, fact_type)
            if regex_fact:
                facts.append(regex_fact)
                log.debug(f"Pattern extracted: {regex_fact}")
            else:
                # Pattern matched but no regex - use basic extraction
                # Find text after the pattern
                for p in self.patterns:
                    if p.get("type") == fact_type and p.get("pattern", "").lower() in text.lower():
                        pat = p.get("pattern", "").lower()
                        idx = text.lower().find(pat)
                        if idx >= 0:
                            after = text[idx + len(pat):].strip(". ").strip()
                            if after and len(after) < 100:
                                facts.append({
                                    "type": fact_type,
                                    "value": after.split(".")[0].split(",")[0],
                                    "method": "pattern",
                                    "confidence": confidence
                                })
                                break

        # Step 2: LLM extraction (hybrid mode, but only for unscanned inputs - skip if pattern matched)
        if call_nvidia_func and self.strategy == "llm_only":
            llm_facts = self.llm_extract_personal_facts(text, call_nvidia_func)
            for lf in llm_facts:
                if not any(f["type"] == lf["type"] for f in facts):
                    facts.append({
                        "type": lf["type"],
                        "value": lf["value"],
                        "method": "llm",
                        "confidence": lf.get("confidence", 0.7)
                    })
        # Note: "hybrid" mode currently uses pattern-only to avoid latency
        # To enable LLM fallback, set strategy: "llm_only" in config

        return facts


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get or create singleton ConfigLoader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_config():
    """Reload configuration from disk."""
    global _config_loader
    _config_loader = ConfigLoader()
    log.info("Configuration reloaded")
