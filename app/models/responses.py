from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchRequest(BaseModel):
    objective: str = "Find the best performing stocks in the market"
    market: str = "US"
    universe: str = "equity"
    research_urls: list[str] = Field(default_factory=list)
    max_candidates: int = Field(default=10, ge=1, le=100)


class AgentProgress(BaseModel):
    type: str = "stage"
    stage: str
    message: str
    data: dict[str, Any] | None = None


class EvidenceResponse(BaseModel):
    ticker: str
    title: str
    url: str
    source_type: str
    claim: str
    content: Any
    published_at: str | None = None
    credibility: float = 0.0


class FundamentalAnalysisResponse(BaseModel):
    ticker: str
    score: float
    metrics: dict[str, Any] = Field(default_factory=dict)
    positives: list[str] = Field(default_factory=list)
    negatives: list[str] = Field(default_factory=list)


class TechnicalAnalysisResponse(BaseModel):
    ticker: str
    score: float
    indicators: dict[str, Any] = Field(default_factory=dict)
    signals: list[str] = Field(default_factory=list)


class NewsEventResponse(BaseModel):
    symbol: str
    event: str
    event_type: str
    summary: str
    published_at: str | None = None
    source: str
    url: str
    source_tier: int
    potential_market_relevance: str
    direction: str
    confidence: float


class NewsResultResponse(BaseModel):
    symbol: str
    material_catalyst_found: bool
    events: list[NewsEventResponse] = Field(default_factory=list)
    contradictory_evidence: list[dict[str, Any]] = Field(default_factory=list)
    search_summary: str


class RankingResponse(BaseModel):
    ticker: str
    fundamental_score: float = 0.0
    technical_score: float = 0.0
    valuation_score: float = 0.0
    risk_score: float = 0.0
    final_score: float = 0.0
    thesis: str = ""
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: list[EvidenceResponse] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    objective: str
    market: str
    universe: str
    research_urls: list[str] = Field(default_factory=list)
    candidate_symbols: list[str] = Field(default_factory=list)
    web_mentions: list[str] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    fundamental_analysis: list[FundamentalAnalysisResponse] = Field(default_factory=list)
    technical_analysis: list[TechnicalAnalysisResponse] = Field(default_factory=list)
    news_results: list[NewsResultResponse] = Field(default_factory=list)
    ranking: list[RankingResponse] = Field(default_factory=list)
    analyses: list[RankingResponse] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
