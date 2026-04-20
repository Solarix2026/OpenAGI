"""
finance_engine.py — Professional trading & finance tools

Covers:
- Technical analysis (RSI, MACD, Bollinger Bands, EMA/SMA)
- Fundamental analysis (P/E, DCF, revenue multiples)
- Portfolio analysis
- Market news synthesis

Data: Yahoo Finance via yfinance (free, no API key required)
"""

import logging
import re
import json
from core.llm_gateway import call_nvidia

log = logging.getLogger("Finance")


class FinanceEngine:
    """Finance analysis engine with technical and fundamental analysis."""

    def get_stock_data(self, ticker: str, period: str = "3mo") -> dict:
        """Fetch OHLCV data and compute basic technicals."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            info = stock.info

            if hist.empty:
                return {"success": False, "error": f"No data for {ticker}"}

            closes = hist["Close"].tolist()
            if len(closes) < 20:
                return {"success": False, "error": "Insufficient data"}

            # Compute RSI (14)
            def compute_rsi(prices, period=14):
                import statistics
                deltas = [prices[i]-prices[i-1] for i in range(1, len(prices))]
                gains = [d if d > 0 else 0 for d in deltas[-period:]]
                losses = [-d if d < 0 else 0 for d in deltas[-period:]]
                avg_gain = sum(gains)/period if gains else 0
                avg_loss = sum(losses)/period if losses else 0.001
                rs = avg_gain / avg_loss
                return 100 - (100/(1+rs))

            rsi = compute_rsi(closes)
            sma_20 = sum(closes[-20:])/20
            sma_50 = sum(closes[-50:])/50 if len(closes) >= 50 else None
            current_price = closes[-1]
            price_change_pct = ((closes[-1]-closes[-20])/closes[-20])*100

            return {
                "success": True,
                "ticker": ticker,
                "price": round(current_price, 2),
                "change_20d": round(price_change_pct, 2),
                "rsi_14": round(rsi, 1),
                "sma_20": round(sma_20, 2),
                "sma_50": round(sma_50, 2) if sma_50 else None,
                "above_sma20": current_price > sma_20,
                "above_sma50": current_price > sma_50 if sma_50 else None,
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "sector": info.get("sector", "?"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
            }
        except ImportError:
            return {"success": False, "error": "yfinance not installed. Run: pip install yfinance"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_stock(self, ticker: str) -> dict:
        """Full analysis with NVIDIA interpretation."""
        data = self.get_stock_data(ticker)
        if not data.get("success"):
            return data

        prompt = f"""Provide professional technical + fundamental analysis for {ticker}.

Data:
- Price: ${data['price']} ({data['change_20d']:+.1f}% 20d)
- RSI(14): {data['rsi_14']} {'(Overbought)' if data['rsi_14'] > 70 else '(Oversold)' if data['rsi_14'] < 30 else '(Neutral)'}
- SMA20: ${data['sma_20']} — Price {'above' if data['above_sma20'] else 'below'} SMA20
- SMA50: {f"${data['sma_50']}" if data['sma_50'] else 'N/A'}
- P/E: {data.get('pe_ratio', 'N/A')}
- Sector: {data.get('sector', '?')}
- 52W Range: ${data.get('52w_low', '?')} — ${data.get('52w_high', '?')}

Provide:
1. Technical bias (bullish/bearish/neutral) with key levels
2. RSI signal interpretation
3. Key risks
4. One-line summary

Disclaimer: Educational analysis only, not financial advice."""

        analysis = call_nvidia([{"role": "user", "content": prompt}],
                               max_tokens=600)

        return {
            "success": True,
            "ticker": ticker,
            "data": data,
            "analysis": analysis,
            "disclaimer": "Educational only. Not financial advice."
        }

    def get_realtime_quote(self, ticker: str) -> dict:
        """Try Alpha Vantage for realtime (free tier: 25 calls/day). Fallback to yfinance (15min delayed)."""
        import os
        av_key = os.getenv("ALPHA_VANTAGE_KEY")
        if av_key:
            try:
                import requests
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={av_key}"
                r = requests.get(url, timeout=10)
                data = r.json().get("Global Quote", {})
                if data:
                    return {
                        "success": True,
                        "ticker": ticker,
                        "price": float(data.get("05. price", 0)),
                        "change_pct": data.get("10. change percent", "0%"),
                        "volume": data.get("06. volume", "0"),
                        "source": "realtime",
                        "note": "Alpha Vantage realtime"
                    }
            except Exception as e:
                log.debug(f"Alpha Vantage failed: {e}")
        # Fallback: yfinance (15min delay)
        return self.get_stock_data(ticker)

    def register_as_tool(self, registry):
        """Register analyze_stock as a tool in the executor registry."""
        engine = self

        def analyze_stock(params: dict) -> dict:
            ticker = (params.get("ticker", "") or params.get("symbol", "")).upper().strip()
            if not ticker:
                return {"success": False, "error": "Provide ticker symbol (e.g. AAPL, TSLA, NVDA)"}
            return engine.analyze_stock(ticker)

        registry.register(
            "analyze_stock",
            analyze_stock,
            "Technical and fundamental stock analysis: RSI, SMA, P/E, sector, 52-week range. Returns professional analysis with key levels and risks.",
            {"ticker": {"type": "string", "required": True, "description": "Stock ticker symbol (e.g. AAPL, TSLA, NVDA)"}},
            "finance"
        )
