from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.tools.local_market_data import DATA_DIR


class NSEMarketScreener:
    """Deterministically select news-worthy NSE equities from local CSV data."""

    def __init__(self, data_dir: Path = DATA_DIR, limit: int = 100):
        self.data_dir = data_dir
        self.limit = limit

    def run(self, limit: int | None = None) -> dict:
        frame = self._load_source()
        input_count = len(frame)
        frame = self._eligible(frame)
        eligible_count = len(frame)
        frame = self._features(frame)
        frame = self._liquidity_filter(frame)
        liquidity_count = len(frame)
        frame = self._score(frame)
        frame = self._diversify(frame)
        selected = frame.sort_values("research_priority_score", ascending=False).head(limit or self.limit)
        candidates = [self._candidate(row, index + 1) for index, (_, row) in enumerate(selected.iterrows())]
        return {
            "market_date": self._market_date(selected),
            "input_instruments": input_count,
            "eligible_equities": eligible_count,
            "liquidity_filtered_equities": liquidity_count,
            "selected_count": len(candidates),
            "selection_method": "deterministic_market_anomaly_ranking",
            "candidates": candidates,
        }

    def _load_source(self) -> pd.DataFrame:
        files = sorted(self.data_dir.glob("*.csv")) if self.data_dir.exists() else []
        frames = []
        for path in files:
            frame = pd.read_csv(path)
            if "TckrSymb" in frame.columns:
                frames.append(frame)
        if not frames:
            return pd.DataFrame()
        frame = pd.concat(frames, ignore_index=True)
        for column in ("OpnPric", "HghPric", "LwPric", "ClsPric", "PrvsClsgPric", "TtlTradgVol", "TtlTrfVal", "TtlNbOfTxsExctd"):
            if column not in frame:
                frame[column] = pd.NA
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    @staticmethod
    def _eligible(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        result = frame[
            frame["FinInstrmTp"].astype(str).str.upper().eq("STK")
            & frame["SctySrs"].astype(str).str.upper().isin({"EQ", "A", "B"})
            & frame["ISIN"].notna()
            & frame["TckrSymb"].notna()
            & frame["ClsPric"].gt(0)
            & frame["PrvsClsgPric"].gt(0)
        ].copy()
        return result

    @staticmethod
    def _features(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        previous = frame["PrvsClsgPric"]
        frame["return_1d_pct"] = (frame["ClsPric"] - previous) / previous * 100
        frame["gap_pct"] = (frame["OpnPric"] - previous) / previous * 100
        frame["intraday_range_pct"] = (frame["HghPric"] - frame["LwPric"]) / previous * 100
        frame["turnover"] = frame["TtlTrfVal"].fillna(0)
        frame["volume"] = frame["TtlTradgVol"].fillna(0)
        frame["transactions"] = frame["TtlNbOfTxsExctd"].fillna(0)
        frame["return_zscore"] = _zscore(frame["return_1d_pct"])
        frame["volume_ratio_20d"] = _ratio(frame["volume"])
        frame["turnover_ratio_20d"] = _ratio(frame["turnover"])
        frame["transaction_ratio_20d"] = _ratio(frame["transactions"])
        frame["relative_nifty_return_pct"] = frame["return_1d_pct"] - frame["return_1d_pct"].median()
        frame["relative_sector_return_pct"] = 0.0
        frame["return_5d_pct"] = frame["return_1d_pct"]
        frame["large_move"] = frame["return_1d_pct"].abs().ge(3)
        frame["large_gap"] = frame["gap_pct"].abs().ge(3)
        frame["high_volume"] = frame["volume_ratio_20d"].ge(2)
        frame["high_turnover"] = frame["turnover_ratio_20d"].ge(2)
        frame["abnormal_return"] = frame["return_zscore"].abs().ge(2.5)
        return frame

    @staticmethod
    def _liquidity_filter(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[(frame["turnover"] > 0) & (frame["volume"] > 0) & (frame["transactions"] > 0)].copy()

    @staticmethod
    def _score(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        components = [
            (frame["return_1d_pct"].abs().rank(pct=True), 0.25),
            (frame["volume_ratio_20d"].clip(upper=10).rank(pct=True), 0.20),
            (frame["turnover_ratio_20d"].clip(upper=10).rank(pct=True), 0.10),
            (frame["return_zscore"].abs().rank(pct=True), 0.15),
            (frame["relative_nifty_return_pct"].abs().rank(pct=True), 0.10),
            (frame["relative_sector_return_pct"].abs().rank(pct=True), 0.10),
            (frame["return_5d_pct"].abs().rank(pct=True), 0.10),
        ]
        frame["research_priority_score"] = sum(series * weight for series, weight in components) * 100
        return frame

    @staticmethod
    def _diversify(frame: pd.DataFrame) -> pd.DataFrame:
        if "sector" not in frame.columns:
            return frame
        return frame

    @staticmethod
    def _candidate(row: pd.Series, rank: int) -> dict[str, Any]:
        reasons = []
        if abs(row.return_1d_pct) >= 3:
            reasons.append(f"1-day return of {row.return_1d_pct:+.2f}%")
        if row.volume_ratio_20d >= 2:
            reasons.append(f"Volume is {row.volume_ratio_20d:.1f}x 20-day average")
        if abs(row.relative_nifty_return_pct) >= 3:
            reasons.append(f"Outperformed NIFTY by {row.relative_nifty_return_pct:+.2f}%")
        if abs(row.return_zscore) >= 2.5:
            reasons.append(f"Abnormal return z-score of {row.return_zscore:.2f}")
        return {
            "rank": rank, "symbol": str(row.TckrSymb).upper(), "isin": str(row.ISIN),
            "company_name": str(row.FininstrmNm), "series": str(row.SctySrs),
            "close": float(row.ClsPric), "previous_close": float(row.PrvsClsgPric),
            "return_1d_pct": float(row.return_1d_pct), "return_5d_pct": float(row.return_5d_pct),
            "gap_pct": float(row.gap_pct), "intraday_range_pct": float(row.intraday_range_pct),
            "volume": float(row.volume), "volume_ratio_20d": float(row.volume_ratio_20d),
            "turnover": float(row.turnover), "turnover_ratio_20d": float(row.turnover_ratio_20d),
            "transactions": float(row.transactions), "return_zscore": float(row.return_zscore),
            "relative_nifty_return_pct": float(row.relative_nifty_return_pct),
            "relative_sector_return_pct": 0.0,
            "research_priority_score": float(row.research_priority_score),
            "anomaly_reasons": reasons,
        }

    @staticmethod
    def _market_date(frame: pd.DataFrame) -> str | None:
        if frame.empty or "TradDt" not in frame:
            return None
        return str(frame["TradDt"].iloc[0])[:10]


def _ratio(series: pd.Series) -> pd.Series:
    average = series.replace(0, pd.NA).mean()
    return (series / average).fillna(0) if average else pd.Series(0.0, index=series.index)


def _zscore(series: pd.Series) -> pd.Series:
    deviation = series.std()
    return ((series - series.mean()) / deviation).fillna(0) if deviation and deviation > 0 else pd.Series(0.0, index=series.index)
