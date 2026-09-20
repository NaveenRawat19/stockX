import re
from urllib.parse import urlparse

from app.market_config import get_market
from app.tools.crawler import fetch_page
from app.tools.local_market_data import rank_local_candidates
from app.tools.nse_market_data import NSEMarketData


TICKER_PATTERN = re.compile(r"\b[A-Z][A-Z0-9&-]{1,9}\b")
NON_TICKERS = {
    "THE", "THIS", "AND", "FOR", "NSE", "BSE", "RSI", "SMA", "TOP", "BEST",
    "STOCK", "STOCKS", "INDIA", "INDIAN", "MARKET", "TODAY", "YEAR",
    "PRICE", "PERFORMING", "PERFORMANCE", "LIST", "PICKS", "BUY",
    "HTTPS", "HTTP", "WWW", "COM", "ORG", "NET", "HTML", "PHP", "INDEX",
    "DATA", "ACTIVE", "HOME", "ABOUT", "LIVE", "SHARE", "ANALYSIS", "HIGH",
    "LOW", "WEEK", "GAINERS", "LOSERS", "MONEYCONTROL", "SCREENER", "INDICES",
    "EQUITY", "INVEST", "INVESTOR", "INVESTORS", "COMPANY", "COMPANIES",
}


class DataResearchAgent:
    """Select and analyze stock data from local files, NSE, or web sources."""

    def __init__(self, candidate_limit: int = 10):
        self.candidate_limit = candidate_limit

    async def run(self, state: dict) -> dict:
        profile = get_market(state.get("market"))
        limit = max(1, min(int(state.get("max_candidates", self.candidate_limit)), self.candidate_limit))
        requested_symbols = {
            str(symbol).upper() for symbol in state.get("candidate_symbols", []) if symbol
        }

        local_result = self._local_result(limit, requested_symbols)
        if local_result:
            return local_result
        if profile.code == "IN" and not state.get("research_urls"):
            return await self._nse_result(state, limit, requested_symbols)
        if requested_symbols:
            state.setdefault("errors", []).append(
                "No local market history was found for the companies identified in news."
            )
            return {"evidence": [], "web_mentions": list(requested_symbols), "candidate_symbols": list(requested_symbols)[:limit]}
        return await self._web_result(state, profile, limit)

    @staticmethod
    def _local_result(limit: int, symbols: set[str] | None = None) -> dict | None:
        candidates = rank_local_candidates(limit, symbols=symbols)
        if not candidates:
            return None
        symbols = [item["symbol"] for item in candidates]
        return {
            "evidence": [
                {
                    "ticker": item["symbol"],
                    "title": "Local historical market data",
                    "url": "data/",
                    "source_type": "local_history",
                    "claim": f"Historical return: {item['return_pct']:.2f}%",
                    "content": item,
                    "published_at": None,
                    "credibility": 0.8,
                }
                for item in candidates
            ],
            "web_mentions": symbols,
            "candidate_symbols": symbols,
        }

    async def _nse_result(self, state: dict, limit: int, requested_symbols: set[str] | None = None) -> dict:
        try:
            source, rows = await NSEMarketData().fetch()
        except Exception as exc:
            error = f"Could not fetch NSE market data: {exc}"
            state.setdefault("errors", []).append(error)
            return {"evidence": [], "web_mentions": [], "candidate_symbols": [], "errors": [error]}

        selected = sorted(
            (row for row in rows if row.get("symbol") and (
                not requested_symbols or str(row["symbol"]).upper() in requested_symbols
            )),
            key=self._percent_change,
            reverse=True,
        )[:limit]
        symbols = [str(row["symbol"]).strip().upper() for row in selected]
        return {
            "evidence": [
                {
                    "ticker": symbol,
                    "title": f"NSE NIFTY 500 ({source})",
                    "url": "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
                    "source_type": source,
                    "claim": f"NSE price change: {self._percent_change(row):.2f}%",
                    "content": row,
                    "published_at": None,
                    "credibility": 0.9,
                }
                for symbol, row in zip(symbols, selected)
            ],
            "web_mentions": symbols,
            "candidate_symbols": symbols,
        }

    async def _web_result(self, state: dict, profile, limit: int) -> dict:
        urls = state.get("research_urls") or profile.urls
        evidence = []
        mentions = []
        seen_mentions = set()
        for raw_url in urls:
            url = f"https:{raw_url}" if raw_url.startswith("//") else raw_url
            if url.strip().lower() == "string":
                continue
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                state.setdefault("errors", []).append(f"Skipped invalid research URL: {url or '<empty>'}")
                continue
            try:
                page = await fetch_page(url)
            except Exception as exc:
                state.setdefault("errors", []).append(f"Could not fetch {url}: {exc}")
                continue
            content = page["content"][:12000]
            tickers = {
                ticker for ticker in TICKER_PATTERN.findall(content.upper())
                if ticker not in NON_TICKERS
            }
            for ticker in tickers:
                if ticker not in seen_mentions:
                    mentions.append(ticker)
                    seen_mentions.add(ticker)
            evidence.append({
                "ticker": next(iter(tickers), "UNKNOWN"),
                "title": page["title"],
                "url": page["url"],
                "source_type": "web",
                "claim": "Web page mentions this security",
                "content": content,
                "published_at": None,
                "credibility": 0.5,
            })
        return {
            "evidence": evidence,
            "web_mentions": mentions,
            "candidate_symbols": mentions[:limit],
        }

    @staticmethod
    def _percent_change(row: dict) -> float:
        if row.get("pChange") is None and row.get("close_price") and row.get("prev_close"):
            return ((row["close_price"] - row["prev_close"]) / row["prev_close"]) * 100
        for key in ("perChange", "pChange", "percentChange", "per"):
            value = row.get(key)
            if value not in (None, ""):
                try:
                    return float(str(value).replace("%", "").replace(",", ""))
                except ValueError:
                    pass
        return 0.0
