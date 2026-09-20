from typing import TypedDict, Annotated
import operator


class Stock(TypedDict):
    ticker: str
    name: str
    exchange: str
    sector: str


class Evidence(TypedDict):
    ticker: str
    title: str
    url: str
    source_type: str

    claim: str
    content: str

    published_at: str | None
    credibility: float


class FundamentalAnalysis(TypedDict):
    ticker: str
    score: float

    metrics: dict
    positives: list[str]
    negatives: list[str]


class TechnicalAnalysis(TypedDict):
    ticker: str
    score: float

    indicators: dict
    signals: list[str]


class RiskAnalysis(TypedDict):
    ticker: str
    score: float

    risks: list[str]
    severity: str


class StockAnalysis(TypedDict):
    ticker: str

    fundamental_score: float
    technical_score: float
    valuation_score: float
    risk_score: float

    final_score: float

    thesis: str
    catalysts: list[str]
    risks: list[str]

    confidence: float

    evidence: list[Evidence]


class InvestmentState(TypedDict):

    # Request
    objective: str
    market: str
    universe: str
    research_urls: list[str]

    # Candidate universe
    candidates: list[Stock]
    candidate_symbols: list[str]

    # Analysis
    fundamental_analysis: Annotated[
        list[FundamentalAnalysis],
        operator.add
    ]

    technical_analysis: Annotated[
        list[TechnicalAnalysis],
        operator.add
    ]

    risk_analysis: Annotated[
        list[RiskAnalysis],
        operator.add
    ]

    # Research
    research_tasks: Annotated[
        list[dict],
        operator.add
    ]

    evidence: Annotated[
        list[Evidence],
        operator.add
    ]

    # Final
    analyses: Annotated[
        list[StockAnalysis],
        operator.add
    ]

    ranking: list[StockAnalysis]

    errors: Annotated[
        list[str],
        operator.add
    ]

    web_mentions: list[str]

    news_results: list[dict]