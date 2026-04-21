# Copyright (c) 2026 ApeironAI
# OpenAGI — An Apeiron Product
# MIT License

"""Natural Language → Structured Query/Command Converter."""
import re
import json
import logging
from datetime import datetime, timedelta

log = logging.getLogger("NLStructured")

def normalize_date(text: str) -> str:
    """Convert relative dates to ISO format."""
    text_lower = text.lower().strip()
    today = datetime.now()
    patterns = [
        (r"today", today),
        (r"tomorrow", today + timedelta(days=1)),
        (r"next monday", today + timedelta(days=(7 - today.weekday()))),
        (r"next friday", today + timedelta(days=(4 - today.weekday()) % 7 + 7 if today.weekday() >= 4 else (4 - today.weekday()))),
        (r"next week", today + timedelta(weeks=1)),
        (r"next month", today.replace(month=today.month % 12 + 1)),
    ]
    for pattern, date in patterns:
        if re.search(pattern, text_lower):
            return date.strftime("%Y-%m-%d")
    # Try to extract explicit dates
    m = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return text  # Return as-is if can't parse

def enhance_search_query(raw_query: str) -> str:
    """Improve search queries with temporal and specificity markers."""
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B %Y")
    # Add temporal marker if not present
    temporal_words = ["latest", "recent", "today", "2024", "2025", "2026", str(current_year)]
    has_temporal = any(w in raw_query.lower() for w in temporal_words)
    enhanced = raw_query
    if not has_temporal:
        enhanced = f"{raw_query} {current_month}"
    # Expand abbreviations
    replacements = {
        " AI ": " artificial intelligence ",
        " ML ": " machine learning ",
        " LLM ": " large language model ",
        " KL ": " Kuala Lumpur Malaysia ",
    }
    for abbr, full in replacements.items():
        enhanced = enhanced.replace(abbr, full)
    return enhanced.strip()

def parse_reminder(text: str) -> dict:
    """Extract reminder details from natural language."""
    # Extract time
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text.lower())
    hour, minute = 9, 0  # defaults
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    # Extract date
    date_str = normalize_date(text)
    # Extract task description (remove time/date parts)
    task = re.sub(r'\b(remind me to|remind me|set a reminder|alert me)\b', '', text, flags=re.I)
    task = re.sub(r'\b(tomorrow|today|next \w+|at \d+(?::\d+)?\s*(?:am|pm)?)\b', '', task, flags=re.I)
    task = re.sub(r'\s+', ' ', task).strip()
    return {
        "task": task or "Reminder",
        "date": date_str,
        "time": f"{hour:02d}:{minute:02d}",
        "cron": f"{minute} {hour} * * *",
        "natural": text
    }

def convert_to_structured(user_input: str, intent_action: str) -> dict:
    """Main converter — takes raw NL input + detected action, returns structured parameters."""
    params = {}
    if intent_action in ("websearch", "news_search", "breaking_news"):
        params["query"] = enhance_search_query(user_input)
    elif intent_action in ("book_flight",):
        # Extract flight details
        origin_m = re.search(r'from\s+([A-Za-z\s]+?)(?:\s+to|\s+on)', user_input, re.I)
        dest_m = re.search(r'to\s+([A-Za-z\s]+?)(?:\s+on|\s+next|\s+$)', user_input, re.I)
        date_m = re.search(r'(?:on|next)\s+(.+?)(?:\s+for|\s+with|$)', user_input, re.I)
        params["from"] = origin_m.group(1).strip() if origin_m else "Kuala Lumpur"
        params["to"] = dest_m.group(1).strip() if dest_m else ""
        params["date"] = normalize_date(date_m.group(1) if date_m else "next friday")
    elif intent_action in ("schedule_task",):
        reminder = parse_reminder(user_input)
        params.update(reminder)
    elif intent_action in ("create_plan",):
        # Extract timeframe
        tf_m = re.search(r'in\s+(\d+\s+(?:day|week|month)s?)', user_input, re.I)
        params["timeframe"] = tf_m.group(1) if tf_m else "1 week"
        params["objective"] = re.sub(r'(?:help me plan|plan for|create a plan for)', '', user_input, flags=re.I).strip()
    return params

def register_nl_converter(kernel):
    """Monkey-patch kernel._run_action to apply NL conversion before execution."""
    original_run_action = kernel._run_action
    def enhanced_run_action(user_input, intent, ctx_str=""):
        action = intent.get("action", "")
        if action and user_input:
            structured_params = convert_to_structured(user_input, action)
            if structured_params:
                # Merge with existing params (structured takes precedence for missing keys)
                existing = intent.get("parameters", {})
                for k, v in structured_params.items():
                    if k not in existing or not existing[k]:
                        existing[k] = v
                intent["parameters"] = existing
                log.debug(f"[NL→Structured] {action}: {list(structured_params.keys())}")
        return original_run_action(user_input, intent, ctx_str)
    kernel._run_action = enhanced_run_action
    log.info("NL→Structured converter active")
