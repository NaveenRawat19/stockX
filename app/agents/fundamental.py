import asyncio

from app.tools.financial_data import LocalFinancialDataProvider


async def fundamental_agent(state):
    provider = state.get("financial_data_provider")
    if provider is None:
        provider = LocalFinancialDataProvider()
    evidence = state.get("evidence", [])
    async def analyze(stock):
        ticker = stock.get("ticker") or stock.get("nse_symbol") or stock.get("bse_code")
        related = [item for item in evidence if item.get("ticker") == ticker]
        try:
            quote = await provider.quote(ticker)
        except Exception as exc:
            quote = {}
            state.setdefault("errors", []).append(f"Fundamental data unavailable for {ticker}: {exc}")

        metrics = {
            "current_price": quote.get("price"),
            "market_cap": quote.get("marketCap"),
            "trailing_pe": quote.get("trailingPE"),
            "price_to_book": quote.get("priceToBook"),
            "return_on_equity": quote.get("returnOnEquity"),
            "debt_to_equity": quote.get("debtToEquity"),
            "web_sources": len(related),
        }
        score = 50.0
        positives = []
        negatives = []
        if metrics["return_on_equity"] is not None:
            if metrics["return_on_equity"] >= 0.15:
                score += 15
                positives.append("Return on equity is above 15%")
            else:
                score -= 10
                negatives.append("Return on equity is below 15%")
        if metrics["debt_to_equity"] is not None:
            if metrics["debt_to_equity"] <= 100:
                score += 10
                positives.append("Debt-to-equity is below 100")
            else:
                score -= 10
                negatives.append("Debt-to-equity is above 100")
        if metrics["trailing_pe"] is not None and 0 < metrics["trailing_pe"] <= 30:
            score += 10
            positives.append("Trailing P/E is at or below 30")
        if related:
            positives.append("Covered by a research source")
        return {"ticker": ticker, "score": score,
            "metrics": metrics, "positives": positives,
            "negatives": negatives or (["Financial metrics unavailable"] if not quote else [])}
    analyses = await asyncio.gather(
        *(analyze(stock) for stock in state.get("candidates", []))
    )
    return {"fundamental_analysis": analyses}
