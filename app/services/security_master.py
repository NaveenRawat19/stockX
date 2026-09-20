from collections.abc import Iterable

from app.models.stocks import Stock


def normalize_stocks(stocks: Iterable[Stock]) -> list[Stock]:
    """Merge duplicate exchange listings by ISIN, then by exchange symbol."""
    normalized: dict[str, Stock] = {}
    for stock in stocks:
        key = stock.isin or stock.nse_symbol or stock.bse_code
        if not key:
            continue
        if key not in normalized:
            normalized[key] = stock.model_copy(deep=True)
            continue
        current = normalized[key]
        current.exchange = sorted(set(current.exchange + stock.exchange))
        current.nse_symbol = current.nse_symbol or stock.nse_symbol
        current.bse_code = current.bse_code or stock.bse_code
        current.isin = current.isin or stock.isin
    return list(normalized.values())


def eligible_equities(stocks: Iterable[Stock]) -> list[Stock]:
    return [
        stock for stock in stocks
        if stock.is_active and stock.is_equity and stock.series in (None, "EQ", "A", "B")
    ]