""" World Bank Open Data API — free, no key required. Indicators: GDP, inflation, unemployment, population growth. """
import requests, logging

log = logging.getLogger("WorldBank")
BASE = "https://api.worldbank.org/v2"
INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "inflation": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "population": "SP.POP.TOTL",
    "co2": "EN.ATM.CO2E.PC",
    "internet_users": "IT.NET.USER.ZS",
}


def get_indicator(country_code: str, indicator: str, years: int = 5) -> dict:
    """country_code: ISO2 e.g. 'MY', 'US', 'CN'"""
    ind_id = INDICATORS.get(indicator.lower(), indicator)
    try:
        r = requests.get(
            f"{BASE}/country/{country_code}/indicator/{ind_id}",
            params={"format": "json", "mrv": years, "per_page": years},
            timeout=10
        )
        data = r.json()
        if len(data) < 2:
            return {"success": False, "error": "No data"}
        records = data[1] or []
        return {
            "success": True,
            "country": country_code,
            "indicator": indicator,
            "data": [{"year": d["date"], "value": d["value"]} for d in records if d["value"] is not None],
            "source": "World Bank Open Data"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_worldbank_tool(registry):
    def worldbank(params: dict) -> dict:
        country = params.get("country", "US")
        indicator = params.get("indicator", "gdp_growth")
        years = int(params.get("years", 5))
        return get_indicator(country, indicator, years)

    registry.register(
        "worldbank_data",
        worldbank,
        "Get World Bank economic data: GDP, inflation, unemployment, population for any country. Free, no API key.",
        {
            "country": {"type": "string", "required": True, "description": "ISO2 country code: MY, US, CN, etc."},
            "indicator": {"type": "string", "default": "gdp_growth", "description": "gdp, gdp_growth, inflation, unemployment, population, co2, internet_users"},
            "years": {"type": "integer", "default": 5}
        },
        "data"
    )
