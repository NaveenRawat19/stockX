from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
DATA_DIR = Path("data")


def load_historical_market_data(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load all supported historical market files from the shared data directory."""
    frames = []
    for path in sorted(data_dir.glob("*")) if data_dir.exists() else []:
        try:
            if path.suffix.lower() == ".parquet":
                frame = pd.read_parquet(path)
            elif path.suffix.lower() in {".csv", ".txt"}:
                frame = pd.read_csv(path)
            else:
                continue
            if not frame.empty:
                frames.append(_normalize_columns(frame))
        except Exception as exc:
            log.warning("Could not read historical file %s: %s", path, exc)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def rank_local_candidates(limit: int = 10, symbols: set[str] | None = None, data_dir: Path = DATA_DIR) -> list[dict]:
    """Rank locally downloaded symbols by available historical return."""
    frame = load_historical_market_data(data_dir)
    if frame.empty or "symbol" not in frame or "close" not in frame:
        return []
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["symbol", "close"])
    if symbols:
        frame = frame[frame["symbol"].astype(str).str.upper().isin(symbols)]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce") if "date" in frame else pd.NaT
    frame = frame.sort_values(["symbol", "date"])
    results = []
    for symbol, group in frame.groupby("symbol", sort=False):
        prices = group["close"].tolist()
        if len(prices) < 2 or prices[0] <= 0:
            continue
        results.append({
            "symbol": str(symbol).strip().upper(),
            "close_price": prices[-1],
            "prev_close": prices[-2],
            "return_pct": (prices[-1] / prices[0] - 1) * 100,
            "observations": len(prices),
        })
    return sorted(results, key=lambda item: item["return_pct"], reverse=True)[:limit]


def load_symbol_history(symbol: str, data_dir: Path = DATA_DIR) -> list[dict]:
    frame = load_historical_market_data(data_dir)
    if frame.empty:
        return []
    frame = frame[frame["symbol"].astype(str).str.upper() == symbol.upper()]
    frame = frame.sort_values("date")
    return [
        {"date": row.date, "close": float(row.close)}
        for row in frame.itertuples()
        if pd.notna(row.close)
    ]


def load_symbol_quote(symbol: str, data_dir: Path = DATA_DIR) -> dict:
    history = load_symbol_history(symbol, data_dir)
    return {"price": history[-1]["close"]} if history else {}


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [
            " ".join(str(part) for part in column if str(part) != "nan").strip()
            for column in frame.columns
        ]
    columns = {str(column).strip().lower(): column for column in frame.columns}
    symbol = _find_column(columns, "ticker", "symbol", "tckrsymb")
    close = _find_column(columns, "close", "adj close", "clspric")
    date = columns.get("date") or columns.get("timestamp") or columns.get("trad_dt")
    if not symbol or not close:
        return pd.DataFrame()
    renamed = frame.rename(columns={symbol: "symbol", close: "close"})
    if date:
        renamed = renamed.rename(columns={date: "date"})
    else:
        renamed["date"] = pd.NaT
    return renamed[["symbol", "close", "date"]]


def _find_column(columns: dict[str, object], *names: str):
    for name in names:
        if name in columns:
            return columns[name]
    for column, original in columns.items():
        if any(column.startswith(f"{name} ") for name in names):
            return original
    return None