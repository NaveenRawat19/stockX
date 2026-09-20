from collections.abc import Iterable

from app.graph.state import InvestmentState
from app.models.stocks import Stock
from app.services.security_master import eligible_equities, normalize_stocks
from app.tools.exchanges.nse import NSEProvider
from app.market_config import get_market


async def universe_agent(state: InvestmentState):

    market = state["market"]
    universe = state["universe"]
    limit = max(1, min(int(state.get("max_candidates", 20)), 100))

    stocks = await get_stock_universe(
        market=market,
        universe=universe,
        limit=limit,
        candidate_symbols=state.get("candidate_symbols", []),
        state=state,
    )

    return {
        "candidates": [stock.model_dump() for stock in stocks],
    }


async def get_stock_universe(
    market: str,
    universe: str,
    limit: int | None = None,
    candidate_symbols: list[str] | None = None,
    state: dict | None = None,
) -> list[Stock]:
    profile = get_market(market)
    if profile.code != "IN":
        symbols = list(dict.fromkeys(candidate_symbols or []))[:limit or 10]
        return [
            Stock(
                company_name=symbol,
                ticker=symbol,
                exchange=[profile.code],
                series="EQ",
            )
            for symbol in symbols
        ]

    providers: list = []
    if profile.code == "IN":
        providers.append(NSEProvider())

    results = await _load_providers(providers)
    stocks = eligible_equities(normalize_stocks(results))
    if universe and universe.lower() not in {"all", "equity", "stocks"}:
        stocks = [stock for stock in stocks if (stock.sector or "").lower() == universe.lower()]
    shortlist = {symbol.upper() for symbol in (candidate_symbols or [])}
    if shortlist:
        matched = [
            stock for stock in stocks
            if (stock.nse_symbol or stock.bse_code or "").upper() in shortlist
        ]
        if matched:
            stocks = matched
            if state is not None:
                state["candidate_symbols"] = [
                    stock.ticker or stock.nse_symbol or stock.bse_code
                    for stock in matched[:limit or 10]
                ]
        else:
            if state is not None:
                state.setdefault("errors", []).append(
                    "Web sources produced no symbols in the exchange universe; "
                    "using the exchange fallback shortlist."
                )
                state["candidate_symbols"] = [
                    stock.ticker or stock.nse_symbol or stock.bse_code
                    for stock in stocks[:limit or 10]
                ]
    return stocks[:limit] if limit else stocks


async def _load_providers(providers: Iterable):
    stocks: list[Stock] = []
    for provider in providers:
        stocks.extend(await provider.get_equity_universe())
    return stocks