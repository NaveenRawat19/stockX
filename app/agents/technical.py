from app.tools.market_data import LocalMarketDataProvider
from app.tools.technical_indicators import technical_snapshot


async def technical_agent(state):
    provider = state.get("market_data_provider")
    if provider is None:
        provider = LocalMarketDataProvider()
    analyses = []
    for stock in state.get("candidates", []):
        ticker = stock.get("ticker") or stock.get("nse_symbol") or stock.get("bse_code")
        try:
            snapshot = technical_snapshot(await provider.history(ticker))
            score = 50.0
            signals = []
            if snapshot["latest_close"] and snapshot["sma_20"]:
                if snapshot["latest_close"] > snapshot["sma_20"]:
                    score += 20
                    signals.append("Price above 20-day average")
                else:
                    score -= 20
                    signals.append("Price below 20-day average")
            if snapshot["rsi_14"] is not None:
                if 45 <= snapshot["rsi_14"] <= 70:
                    score += 10
                    signals.append("RSI supports momentum")
                elif snapshot["rsi_14"] > 70:
                    signals.append("RSI indicates overbought conditions")
            analyses.append({"ticker": ticker, "score": max(0.0, min(100.0, score)),
                             "indicators": snapshot, "signals": signals})
        except Exception as exc:
            analyses.append({"ticker": ticker, "score": 0.0, "indicators": {},
                             "signals": [f"Technical data unavailable: {exc}"]})
    return {"technical_analysis": analyses}
