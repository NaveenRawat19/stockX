def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def relative_strength_index(values: list[float], window: int = 14) -> float | None:
    if len(values) <= window:
        return None
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(change, 0) for change in changes[-window:]]
    losses = [abs(min(change, 0)) for change in changes[-window:]]
    average_loss = sum(losses) / window
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + (sum(gains) / window) / average_loss))


def technical_snapshot(history: list[dict]) -> dict:
    closes = [float(item["close"]) for item in history]
    latest = closes[-1] if closes else None
    sma_20 = moving_average(closes, 20)
    sma_50 = moving_average(closes, 50)
    return {
        "latest_close": latest,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "rsi_14": relative_strength_index(closes),
    }
