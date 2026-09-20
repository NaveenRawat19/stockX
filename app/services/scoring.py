def rank_stocks(state):
    fundamentals = {item["ticker"]: item for item in state.get("fundamental_analysis", [])}
    technicals = {item["ticker"]: item for item in state.get("technical_analysis", [])}
    ranking = []
    for stock in state.get("candidates", []):
        ticker = stock.get("ticker") or stock.get("nse_symbol") or stock.get("bse_code")
        fundamental = fundamentals.get(ticker, {"score": 0})
        technical = technicals.get(ticker, {"score": 0})
        final_score = 0.55 * fundamental["score"] + 0.45 * technical["score"]
        ranking.append({"ticker": ticker, "fundamental_score": fundamental["score"],
                        "technical_score": technical["score"], "valuation_score": 0.0,
                        "risk_score": 0.0, "final_score": final_score,
                        "thesis": "Web evidence combined with fundamental and technical signals.",
                        "catalysts": fundamental.get("positives", []),
                        "risks": fundamental.get("negatives", []), "confidence": 0.5,
                        "evidence": [item for item in state.get("evidence", []) if item.get("ticker") == ticker]})
    return {"ranking": sorted(ranking, key=lambda item: item["final_score"], reverse=True),
            "analyses": ranking}
