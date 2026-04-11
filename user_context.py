"""
user_context.py — Real-time geo + weather context injection

Provides location-aware, time-aware context prepended to all NVIDIA calls.
This makes every response geographically and situationally grounded.

Priority for location:
  1. USER_CITY env var (explicit override)
  2. ip-api.com geolocation (free, no key)
  3. Cache from last successful lookup
"""
import os, requests, json, logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("UserContext")
CACHE_PATH = Path("./workspace/user_context.json")


class UserContextProvider:
    def __init__(self):
        self._cache = self._load_cache()
        self._location = None
        self._weather = None

    def get_location(self) -> dict:
        if os.getenv("USER_CITY"):
            return {
                "city": os.getenv("USER_CITY"),
                "country": os.getenv("USER_COUNTRY", ""),
                "source": "env"
            }

        try:
            r = requests.get(
                "http://ip-api.com/json/?fields=city,country,lat,lon,timezone,isp",
                timeout=4
            )
            if r.status_code == 200:
                data = r.json()
                data["source"] = "ip_geo"
                self._save_cache({"location": data})
                return data
        except Exception as e:
            log.debug(f"Geo lookup failed: {e}")

        return self._cache.get("location", {"city": "Kuala Lumpur", "country": "MY"})

    def get_weather(self, city: str = None) -> dict:
        if not city:
            city = self.get_location().get("city", "Kuala Lumpur")

        try:
            r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=5)
            if r.status_code == 200:
                d = r.json()["current_condition"][0]
                return {
                    "city": city,
                    "temp_c": d["temp_C"],
                    "feels_like": d["FeelsLikeC"],
                    "condition": d["weatherDesc"][0]["value"],
                    "humidity": d["humidity"],
                    "summary": f"{d['temp_C']}°C, {d['weatherDesc'][0]['value']}"
                }
        except Exception:
            pass

        try:
            r = requests.get(f"https://wttr.in/{city}?format=3", timeout=4)
            return {"city": city, "summary": r.text.strip()}
        except Exception:
            return {"city": city, "summary": "weather unavailable"}

    def get_time_context(self) -> dict:
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
        """Compact string prepended to all NVIDIA system prompts."""
        loc = self.get_location()
        weather = self.get_weather(loc.get("city"))
        t = self.get_time_context()

        return (
            f"[Context: {t['greeting']}. "
            f"Location: {loc.get('city','?')}, {loc.get('country','')}. "
            f"Weather: {weather.get('summary','?')}. "
            f"Time: {t['time_str']}]"
        )

    def _load_cache(self) -> dict:
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            return {}

    def _save_cache(self, data: dict):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps({**self._cache, **data}, indent=2))
