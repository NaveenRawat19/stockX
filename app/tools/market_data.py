from app.tools.local_market_data import load_symbol_history


class LocalMarketDataProvider:
	async def history(self, symbol: str, days: int = 180) -> list[dict]:
		return load_symbol_history(symbol)[-days:]


__all__ = ["LocalMarketDataProvider"]
