from pydantic import BaseModel, Field
from typing import Optional


class Stock(BaseModel):
    isin: Optional[str] = None
    company_name: str
    ticker: Optional[str] = None
    nse_symbol: Optional[str] = None
    bse_code: Optional[str] = None
    exchange: list[str] = Field(default_factory=list)
    series: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    is_active: bool = True
    is_equity: bool = True
    last_updated: Optional[str] = None