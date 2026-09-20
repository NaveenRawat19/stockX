from dataclasses import dataclass


@dataclass(frozen=True)
class MarketProfile:
    code: str
    country: str
    label: str
    exchange: str | None
    search_name: str
    urls: tuple[str, ...]


MARKETS = {
    "US": MarketProfile(
        "US", "United States", "US equities", None, "US", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://finviz.com/screener.ashx?v=111&s=ta_topgainers",
            "https://www.cnbc.com/quotes/most-active/",
        ),
    ),
    "IN": MarketProfile(
        "IN", "India", "India equities", "NSE", "Indian", (
            "https://www.nseindia.com/market-data/top-gainers-losers",
            "https://www.nseindia.com/market-data/52-week-high-equity-market",
            "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.php",
        ),
    ),
    "GB": MarketProfile(
        "GB", "United Kingdom", "UK equities", "LSE", "UK", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.hl.co.uk/shares/stock-market-summary/ftse-100",
        ),
    ),
    "CA": MarketProfile(
        "CA", "Canada", "Canadian equities", "TSX", "Canadian", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.tsx.com/listings/listing-with-us",
        ),
    ),
    "AU": MarketProfile(
        "AU", "Australia", "Australian equities", "ASX", "Australian", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.asx.com.au/markets/market-resources/top-traded",
        ),
    ),
    "DE": MarketProfile(
        "DE", "Germany", "German equities", "XETRA", "German", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.boerse-frankfurt.de/en/indices/dax",
        ),
    ),
    "JP": MarketProfile(
        "JP", "Japan", "Japanese equities", "TSE", "Japanese", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.jpx.co.jp/english/markets/statistics-equities/index.html",
        ),
    ),
    "HK": MarketProfile(
        "HK", "Hong Kong", "Hong Kong equities", "HKEX", "Hong Kong", (
            "https://finance.yahoo.com/markets/stocks/most-active/",
            "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities",
        ),
    ),
}

ALIASES = {
    "USA": "US", "UNITED STATES": "US", "AMERICA": "US",
    "INDIA": "IN", "NSE": "IN", "BSE": "IN",
    "UK": "GB", "UNITED KINGDOM": "GB", "LONDON": "GB",
    "CANADA": "CA", "TORONTO": "CA",
    "AUSTRALIA": "AU", "ASX": "AU",
    "GERMANY": "DE", "XETRA": "DE",
    "JAPAN": "JP", "TOKYO": "JP",
    "HONG KONG": "HK", "HKEX": "HK",
}


def get_market(value: str | None) -> MarketProfile:
    key = (value or "US").strip().upper()
    key = ALIASES.get(key, key)
    try:
        return MARKETS[key]
    except KeyError as exc:
        supported = ", ".join(MARKETS)
        raise ValueError(f"Unsupported market '{value}'. Choose one of: {supported}") from exc


def market_options() -> list[dict[str, str]]:
    return [
        {"code": profile.code, "country": profile.country, "label": profile.label}
        for profile in MARKETS.values()
    ]
