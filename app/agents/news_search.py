from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.tools.crawler import fetch_page
from app.tools.web_search import search_web
from app.market_config import get_market


class NewsWebSearchAgent:
    """Find recent, source-backed news for market-data-selected symbols."""

    def __init__(self, max_queries_per_symbol: int = 5, max_results_per_query: int = 5, max_pages: int = 50):
        self.max_queries_per_symbol = max_queries_per_symbol
        self.max_results_per_query = max_results_per_query
        self.max_pages = max_pages

    async def run(self, state: dict) -> dict:
        results = []
        candidates = state.get("candidates", [])
        if not candidates:
            return await self._discover_news_companies(state)
        movement = self._movement_context(state)
        pages_used = 0
        for candidate in candidates:
            symbol = self._symbol(candidate)
            if not symbol:
                continue
            stock_results, pages_used = await self._search_symbol(
                symbol, movement.get(symbol, 0.0), state, pages_used
            )
            results.append({
                "symbol": symbol,
                "material_catalyst_found": any(self._is_material(event) for event in stock_results),
                "events": self._deduplicate(stock_results),
                "contradictory_evidence": [],
                "search_summary": self._summary(stock_results),
            })
        return {"news_results": results}

    async def _discover_news_companies(self, state: dict) -> dict:
        profile = get_market(state.get("market"))
        limit = max(1, min(int(state.get("max_candidates", 10)), 10))
        queries = [
            f"{profile.search_name} stocks latest financial news earnings orders",
            f"{profile.search_name} stocks latest regulatory corporate announcements",
            f"{profile.search_name} market moving company news today",
        ][:self.max_queries_per_symbol]
        symbols = []
        seen = set()
        results = []
        pages_used = 0
        for query in queries:
            try:
                search_results = await search_web(query, limit=self.max_results_per_query)
            except Exception as exc:
                state.setdefault("errors", []).append(f"News discovery failed: {exc}")
                continue
            for result in search_results:
                if pages_used >= self.max_pages:
                    break
                pages_used += 1
                text = f"{result.get('title', '')} {result.get('snippet', '')}".upper()
                found = [
                    symbol for symbol in re.findall(r"\b[A-Z][A-Z0-9&-]{1,9}\b", text)
                    if symbol not in self._non_tickers()
                ]
                if not found:
                    continue
                symbol = found[0]
                event = await self._extract_event(symbol, result)
                if event:
                    results.append(event)
                if symbol not in seen:
                    symbols.append(symbol)
                    seen.add(symbol)
                if len(symbols) >= limit:
                    break
            if len(symbols) >= limit:
                break
        grouped = []
        for symbol in symbols[:limit]:
            events = self._deduplicate([event for event in results if event["symbol"] == symbol])
            grouped.append({
                "symbol": symbol,
                "material_catalyst_found": any(self._is_material(event) for event in events),
                "events": events,
                "contradictory_evidence": [],
                "search_summary": self._summary(events),
            })
        return {"news_results": grouped, "candidate_symbols": symbols[:limit], "web_mentions": symbols[:limit]}

    @staticmethod
    def _non_tickers():
        return {
            "THE", "AND", "FOR", "TOP", "BEST", "STOCK", "STOCKS", "MARKET",
            "NEWS", "LATEST", "FINANCIAL", "FINANCIALS", "EARNINGS", "TODAY",
            "COMPANY", "COMPANIES", "ORDER", "ORDERS", "REGULATORY", "CORPORATE",
            "ANNOUNCEMENTS", "MOVING", "INDIA", "INDIAN", "NSE", "BSE", "US",
            "CNBC", "TRENDING", "REPORTS", "ZACKS", "CALENDAR", "SEC", "PRESS",
            "TMX", "MOVERS", "GAINING", "GAINERS", "LOSERS", "LIVE", "STOCKS",
            "NASDAQ", "NYSE", "SP500", "SPX", "ETF", "INDEX", "INDICES", "QUOTE",
        }

    async def _search_symbol(self, symbol: str, change: float, state: dict, pages_used: int) -> tuple[list[dict], int]:
        direction = "rose" if change > 0 else "fell" if change < 0 else "moved"
        queries = [
            f"{symbol} latest news announcement",
            f"{symbol} company results order contract",
            f"{symbol} regulatory legal exchange filing",
            f"{symbol} sector competitor news",
            f"{symbol} {direction} catalyst",
        ][:self.max_queries_per_symbol]
        events = []
        for query in queries:
            try:
                search_results = await search_web(query, limit=self.max_results_per_query)
            except Exception as exc:
                state.setdefault("errors", []).append(f"News search failed for {symbol}: {exc}")
                continue
            for result in search_results:
                if pages_used >= self.max_pages:
                    return events, pages_used
                pages_used += 1
                event = await self._extract_event(symbol, result)
                if event:
                    events.append(event)
        return events, pages_used

    async def _extract_event(self, symbol: str, result: dict) -> dict | None:
        url = result.get("url", "")
        if url.startswith("//"):
            url = f"https:{url}"
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        title = str(result.get("title", "")).strip()
        snippet = str(result.get("snippet", "")).strip()
        published_at = self._publication_date(result)
        source_tier = self._source_tier(parsed.netloc)
        event_type = self._event_type(f"{title} {snippet}")
        direction = self._direction(f"{title} {snippet}")
        try:
            page = await fetch_page(url)
            summary = self._compact_summary(page.get("content", ""), snippet)
            published_at = published_at or self._publication_date(page)
            canonical_url = page.get("url", url)
        except Exception:
            summary = snippet or title
            canonical_url = url
        if not summary:
            return None
        return {
            "symbol": symbol,
            "event": title or "Recent market-related development",
            "event_type": event_type,
            "summary": summary[:1000],
            "published_at": published_at,
            "source": parsed.netloc,
            "url": canonical_url,
            "source_tier": source_tier,
            "potential_market_relevance": "high" if source_tier == 1 else "medium" if source_tier == 2 else "low",
            "direction": direction,
            "confidence": 0.85 if source_tier == 1 else 0.7 if source_tier == 2 else 0.45,
        }

    @staticmethod
    def _movement_context(state: dict) -> dict[str, float]:
        context = {}
        for item in state.get("evidence", []):
            ticker = item.get("ticker")
            content = item.get("content", {})
            if ticker and isinstance(content, dict):
                value = content.get("return_pct") or content.get("pChange")
                try:
                    context[ticker] = float(value)
                except (TypeError, ValueError):
                    context[ticker] = 0.0
        return context

    @staticmethod
    def _symbol(candidate: dict) -> str:
        return str(candidate.get("ticker") or candidate.get("nse_symbol") or candidate.get("bse_code") or "").upper()

    @staticmethod
    def _source_tier(host: str) -> int:
        host = host.lower()
        if any(name in host for name in ("nseindia.com", "bseindia.com", "sebi.gov.in", "rbi.org.in", ".gov")):
            return 1
        if any(name in host for name in ("reuters.com", "bloomberg.com", "economictimes.indiatimes.com", "business-standard.com", "moneycontrol.com")):
            return 2
        return 3

    @staticmethod
    def _event_type(text: str) -> str:
        text = text.lower()
        for keywords, event_type in (
            (("result", "earnings", "profit", "revenue"), "earnings"),
            (("sebi", "regulator", "approval", "compliance"), "regulatory"),
            (("court", "lawsuit", "litigation"), "legal"),
            (("order", "contract", "customer", "partnership"), "company_development"),
            (("acquisition", "merger", "stake", "divest"), "corporate_action"),
            (("competitor", "market share", "rival"), "competitor"),
        ):
            if any(keyword in text for keyword in keywords):
                return event_type
        return "other"

    @staticmethod
    def _direction(text: str) -> str:
        text = text.lower()
        positive = ("growth", "wins", "order", "approval", "profit", "upgrade", "surge")
        negative = ("loss", "decline", "penalty", "probe", "downgrade", "lawsuit", "warning")
        has_positive = any(word in text for word in positive)
        has_negative = any(word in text for word in negative)
        return "mixed" if has_positive and has_negative else "positive" if has_positive else "negative" if has_negative else "unknown"

    @staticmethod
    def _publication_date(source: dict) -> str | None:
        for key in ("published_at", "published", "date", "publishedAt"):
            value = source.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _compact_summary(content: str, fallback: str) -> str:
        text = re.sub(r"\s+", " ", content).strip()
        return text[:1000] if text else fallback

    @staticmethod
    def _deduplicate(events: list[dict]) -> list[dict]:
        unique = {}
        for event in events:
            key = hashlib.sha1(
                f"{event['symbol']}|{event['event']}|{event['summary'][:160]}".lower().encode()
            ).hexdigest()
            unique.setdefault(key, event)
        return list(unique.values())[:20]

    @staticmethod
    def _summary(events: list[dict]) -> str:
        if not events:
            return "No material recent catalyst identified from available web sources."
        return f"Found {len(events)} recent source-backed development(s); causality was not inferred."

    @staticmethod
    def _is_material(event: dict) -> bool:
        return (
            event.get("event_type") != "other"
            and event.get("potential_market_relevance") in {"high", "medium"}
        )
