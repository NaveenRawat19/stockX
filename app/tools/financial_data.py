from app.tools.local_market_data import load_symbol_quote


class LocalFinancialDataProvider:
	async def quote(self, symbol: str) -> dict:
		return load_symbol_quote(symbol)


__all__ = ["LocalFinancialDataProvider"]
