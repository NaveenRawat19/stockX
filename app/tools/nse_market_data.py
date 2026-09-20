from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytz
from jugaad_data.nse import bhavcopy_save
from nsepython import nsefetch

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
LIVE_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"


class NSEMarketData:
    """Fetch normalized NIFTY 500 data from live NSE or the latest bhavcopy."""

    def __init__(self, cache_ttl_seconds: int | None = None):
        self.cache_ttl_seconds = cache_ttl_seconds or int(
            os.getenv("NSE_CACHE_TTL_SECONDS", "150")
        )
        self._cache: tuple[float, str, list[dict]] | None = None
        self._cache_lock = asyncio.Lock()

    async def fetch(self) -> tuple[str, list[dict]]:
        async with self._cache_lock:
            now = asyncio.get_running_loop().time()
            if self._cache and now - self._cache[0] < self.cache_ttl_seconds:
                logger.info("NSE market data source=%s rows=%d (cached)", self._cache[1], len(self._cache[2]))
                return self._cache[1], self._cache[2]

            rows: list[dict] = []
            source = "bhavcopy_fallback"
            if self.market_is_open():
                try:
                    rows = await asyncio.to_thread(self._fetch_live)
                    if rows:
                        source = "live"
                except Exception as exc:
                    logger.warning("NSE live fetch failed; using bhavcopy: %s", exc)

            if not rows:
                rows = await asyncio.to_thread(self._fetch_latest_bhavcopy)
                source = "bhavcopy_fallback"

            self._cache = (now, source, rows)
            logger.info("NSE market data source=%s rows=%d", source, len(rows))
            return source, rows

    @staticmethod
    def market_is_open(now: datetime | None = None) -> bool:
        current = now.astimezone(IST) if now else datetime.now(IST)
        return current.weekday() < 5 and (9, 15) <= (current.hour, current.minute) <= (15, 30)

    @staticmethod
    def _fetch_live() -> list[dict]:
        payload = nsefetch(LIVE_URL)
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", [])
        if not isinstance(data, list):
            return []
        return [NSEMarketData._normalize_live(row) for row in data if isinstance(row, dict)]

    @staticmethod
    def _normalize_live(row: dict) -> dict:
        close_price = row.get("lastPrice")
        previous = row.get("previousClose") or row.get("prevClose")
        return {
            "symbol": str(row.get("symbol", "")).strip().upper(),
            "close_price": _number(close_price),
            "prev_close": _number(previous),
            "pChange": _number(row.get("pChange")),
            "volume": _number(row.get("totalTradedVolume") or row.get("totalTradedVolume")),
        }

    @staticmethod
    def _fetch_latest_bhavcopy(max_days: int = 30) -> list[dict]:
        folder = Path(os.getenv("NSE_BHAVCOPY_DIR", ".nse_bhavcopy"))
        folder.mkdir(parents=True, exist_ok=True)
        current = datetime.now(IST).date()
        last_error: Exception | None = None
        for offset in range(max_days):
            trading_day = current - timedelta(days=offset)
            try:
                path = bhavcopy_save(trading_day, dest=str(folder))
                frame = _read_bhavcopy(path, folder, trading_day)
                rows = [
                    _normalize_bhavcopy(row)
                    for row in frame.to_dict(orient="records")
                ]
                rows = [row for row in rows if row["symbol"] and row["close_price"] is not None]
                if rows:
                    return rows
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"No valid NSE bhavcopy found in the last {max_days} days: {last_error}")


def _read_bhavcopy(path: Any, folder: Path, trading_day: date) -> pd.DataFrame:
    if path:
        candidate = Path(path)
        if candidate.exists():
            return _read_market_file(candidate)
    matches = sorted(folder.glob("*"))
    for candidate in reversed(matches):
        if candidate.is_file():
            try:
                return _read_market_file(candidate)
            except Exception:
                continue
    raise FileNotFoundError(f"Bhavcopy file missing for {trading_day}")


def _read_market_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        return pd.read_csv(path, compression="zip")
    return pd.read_csv(path)


def _normalize_bhavcopy(row: dict) -> dict:
    return {
        "symbol": str(row.get("TckrSymb") or row.get("SYMBOL") or "").strip().upper(),
        "close_price": _number(row.get("ClsPric") or row.get("CLOSE")),
        "prev_close": _number(row.get("PrvsClsgPric") or row.get("PREV_CLOSE")),
        "pChange": _number(row.get("pChange")),
        "volume": _number(row.get("TtlTradgVol") or row.get("TOTTRDQTY") or row.get("VOLUME")),
    }


def _number(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None
