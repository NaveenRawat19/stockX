import io
import httpx
import pandas as pd

from app.models.stocks import Stock
from .base import ExchangeProvider


class NSEProvider(ExchangeProvider):

    SECURITIES_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

    async def get_equity_universe(self):

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "stock-research-agent/1.0"}
        ) as client:

            response = await client.get(
                self.SECURITIES_URL
            )

            response.raise_for_status()

            content = response.content

            if b"<html" in content[:500].lower():
                raise ValueError("NSE returned an HTML page instead of the equity CSV")

        return self._parse(content)

    def _parse(self, content: bytes):

        df = pd.read_csv(
            io.BytesIO(content)
        )

        stocks = []

        for _, row in df.iterrows():

            company_name = row.get("NAME OF COMPANY")
            symbol = row.get("SYMBOL")
            if pd.isna(company_name) or pd.isna(symbol):
                continue

            stocks.append(Stock(
                isin=None if pd.isna(row.get("ISIN")) else str(row.get("ISIN")),
                company_name=str(company_name).strip(),
                nse_symbol=str(symbol).strip(),
                series=None if pd.isna(row.get("SERIES")) else str(row.get("SERIES")),
                exchange=["NSE"],
            ))

        return stocks