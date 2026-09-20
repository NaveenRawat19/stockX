import io

import httpx
import pandas as pd

from app.models.stocks import Stock
from .base import ExchangeProvider


class BSEProvider(ExchangeProvider):
	"""Loads the BSE equity master from its downloadable CSV endpoint."""

	SECURITIES_URL = "https://www.bseindia.com/downloads/Help/file/Equity.csv"

	async def get_equity_universe(self):
		async with httpx.AsyncClient(
			timeout=30,
			follow_redirects=True,
			headers={"User-Agent": "stock-research-agent/1.0"},
		) as client:
			response = await client.get(self.SECURITIES_URL)
			response.raise_for_status()
		return self._parse(response.content)

	def _parse(self, content: bytes):
		frame = pd.read_csv(io.BytesIO(content), encoding_errors="ignore")
		columns = {str(column).strip().upper(): column for column in frame.columns}
		code_column = columns.get("SECURITY CODE") or columns.get("SCRIP CODE")
		name_column = columns.get("SECURITY NAME") or columns.get("NAME OF COMPANY")
		if not code_column or not name_column:
			raise ValueError("BSE equity file does not contain security code and name columns")

		stocks = []
		for _, row in frame.iterrows():
			code = row.get(code_column)
			name = row.get(name_column)
			if pd.isna(code) or pd.isna(name):
				continue
			stocks.append(Stock(
				company_name=str(name).strip(),
				bse_code=str(code).split(".")[0].strip(),
				exchange=["BSE"],
			))
		return stocks
