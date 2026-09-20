# Stock Research Agent

The agent researches configured market pages, selects a shortlist of stocks,
reads local historical data from `data/`, then ranks stocks using technical and
available fundamental signals.

## Run

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Historical and screening data is read from the local `data/` directory.

POST a request to `/api/research`:

```json
{
	"objective": "Find the best performing US stocks",
	"market": "US",
	"universe": "equity",
	"research_urls": [],
	"max_candidates": 10
}
```

For long-running requests, use the WebSocket endpoint `/api/research/ws`.
Connect, send the same JSON request as above, then handle `started`,
`keepalive`, and `complete` messages. The final result is in the `data` field
of the `complete` message. The workflow searches the web first for the top
performing ten ticker symbols, then loads the matching exchange records and
uses the local historical dataset for that shortlist.

The workflow is implemented with LangGraph nodes:
`web_research -> universe -> fundamental -> technical -> scoring`.
Print the nodes or Mermaid diagram with:

```powershell
python -c "from app.graph.graph import build_workflow; graph=build_workflow(); print(list(graph.get_graph().nodes)); print(graph.get_graph().draw_mermaid())"
```

Set `research_urls` to inspect specific pages. When it is empty, the agent uses
market-specific research pages. Supported market codes are `US`, `IN`, `GB`,
`CA`, `AU`, `DE`, `JP`, and `HK`; country names and common exchange aliases are
also accepted. India uses the NSE security master, while other markets use the
web shortlist and the selected exchange code for market-specific processing.
For India, leaving `research_urls` empty uses NSE's live top-gainers API through
`nsepython` and sends the best-performing symbols into the analysis agents.

Historical files are always stored and read from `data/`. The downloader writes
`data/us_stock_data.parquet` and `data/us_stock_progress.csv`; the research
agent reads CSV and Parquet files in that same directory and ranks candidates
from their available historical returns before using remote discovery.
