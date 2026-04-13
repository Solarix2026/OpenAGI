# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
user_context.py — Real-time geo + weather context injection v2.0 (TTL Cache)

Provides location-aware, time-aware context prepended to all NVIDIA calls.
Performance: All lookups cached with TTL to avoid repeated API calls.

TTL Strategy:
- Location: 1 hour (doesn't change often)
- Weather: 30 minutes (changes gradually)
- Context string: 5 minutes (aggregated)
"""
import os, requests, json, logging, time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("UserContext")
CACHE_PATH = Path("./workspace/user_context.json")


class UserContextProvider:
    # TTL in seconds
    _LOCATION_TTL = 3600      # 1 hour
    _WEATHER_TTL = 1800       # 30 minutes
    _CTX_STR_TTL = 300        # 5 minutes

    def __init__(self):
        self._cache = self._load_cache()
        self._location_val = None
        self._location_ts = 0.0
        self._weather_val = None
        self._weather_ts = 0.0
        self._weather_city = None
        self._ctx_str_val = None
        self._ctx_str_ts = 0.0

    def get_location(self) -> dict:
        """Get location with 1-hour TTL cache."""
        # Check env override (always fresh)
        if os.getenv("USER_CITY"):
            return {
                "city": os.getenv("USER_CITY"),
                "country": os.getenv("USER_COUNTRY", ""),
                "source": "env"
            }

        # Return cached if not expired
        if self._location_val and (time.time() - self._location_ts) < self._LOCATION_TTL:
            return self._location_val

        # Fetch fresh
        try:
            r = requests.get(
                "http://ip-api.com/json/?fields=city,country,lat,lon,timezone,isp",
                timeout=4
            )
            if r.status_code == 200:
                data = r.json()
                data["source"] = "ip_geo"
                self._save_cache({"location": data})
                self._location_val = data
                self._location_ts = time.time()
                return data
        except Exception as e:
            log.debug(f"Geo lookup failed: {e}")

        # Fallback to cache file or default
        cached = self._cache.get("location", {"city": "Kuala Lumpur", "country": "MY"})
        self._location_val = cached
        self._location_ts = time.time()
        return cached

    def get_weather(self, city: str = None) -> dict:
        """Get weather with 30-minute TTL cache."""
        if not city:
            city = self.get_location().get("city", "Kuala Lumpur")

        # Return cached if same city and not expired
        if (self._weather_val and self._weather_city == city and
            (time.time() - self._weather_ts) < self._WEATHER_TTL):
            return self._weather_val

        # Fetch fresh
        result = None
        try:
            r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=5)
            if r.status_code == 200:
                d = r.json()["current_condition"][0]
                result = {
                    "city": city,
                    "temp_c": d["temp_C"],
                    "feels_like": d["FeelsLikeC"],
                    "condition": d["weatherDesc"][0]["value"],
                    "humidity": d["humidity"],
                    "summary": f"{d['temp_C']}°C, {d['weatherDesc'][0]['value']}"
                }
        except Exception:
            pass

        if not result:
            try:
                r = requests.get(f"https://wttr.in/{city}?format=3", timeout=4)
                result = {"city": city, "summary": r.text.strip()}
            except Exception:
                result = {"city": city, "summary": "weather unavailable"}

        self._weather_val = result
        self._weather_city = city
        self._weather_ts = time.time()
        return result

    def get_time_context(self) -> dict:
        """Time context (always fresh, no external call)."""
        h = datetime.now().hour
        if 5 <= h < 12:
            period, greeting = "morning", "Good morning"
        elif 12 <= h < 17:
            period, greeting = "afternoon", "Good afternoon"
        elif 17 <= h < 21:
            period, greeting = "evening", "Good evening"
        else:
            period, greeting = "night", "You're up late"

        return {
            "hour": h,
            "period": period,
            "greeting": greeting,
            "is_late_night": h >= 23 or h < 4,
            "time_str": datetime.now().strftime("%H:%M")
        }

    def build_context_string(self) -> str:
        """Compact string preprended to all NVIDIA system prompts (5-min TTL)."""
        # Return cached if not expired
        if self._ctx_str_val and (time.time() - self._ctx_str_ts) < self._CTX_STR_TTL:
            return self._ctx_str_val

        loc = self.get_location()
        weather = self.get_weather(loc.get("city"))
        t = self.get_time_context()

        result = (
            f"[Context: {t['greeting']}. "
            f"Location: {loc.get('city','?')}, {loc.get('country','')}. "
            f"Weather: {weather.get('summary','?')}. "
            f"Time: {t['time_str']}]"
        )

        self._ctx_str_val = result
        self._ctx_str_ts = time.time()
        return result

    def _load_cache(self) -> dict:
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            return {}

    def _save_cache(self, data: dict):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps({**self._cache, **data}, indent=2))
