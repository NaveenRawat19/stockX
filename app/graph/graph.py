from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from app.agents.data_research import DataResearchAgent
from app.agents.news_search import NewsWebSearchAgent
from app.agents.classes import (
	FundamentalAgent,
	ScoringAgent,
	TechnicalAgent,
	UniverseAgent,
	WebResearchAgent,
)
from app.graph.state import InvestmentState
from app.market_config import get_market


ProgressCallback = Callable[[str, str, dict | None], Awaitable[None]]


def build_workflow(on_progress: ProgressCallback | None = None):
	"""Build the web-first stock research graph."""
	research_agent = DataResearchAgent()
	universe_agent = UniverseAgent()
	news_agent = NewsWebSearchAgent()
	fundamental_agent = FundamentalAgent()
	technical_agent = TechnicalAgent()
	scoring_agent = ScoringAgent()

	async def progress(stage: str, message: str, data: dict | None = None):
		if on_progress is not None:
			await on_progress(stage, message, data)

	async def news_search_node(state):
		await progress("news_search", "Finding relevant financial news first")
		result = await news_agent.run(state)
		await progress("news_search", "News discovery complete", {
			"results": result.get("news_results", []),
		})
		return result

	async def market_data_node(state):
		await progress("market_data", "Fetching market data for news companies")
		result = await research_agent.run(state)
		await progress("market_data", "Market data fetch complete", {
			"candidate_symbols": result.get("candidate_symbols", []),
			"sources": len(result.get("evidence", [])),
		})
		return result

	async def universe_node(state):
		await progress("universe", "Building the candidate shortlist")
		result = await universe_agent.run(state)
		await progress("universe", "Candidate shortlist ready", {
			"candidates": [item.get("ticker") or item.get("nse_symbol") or item.get("bse_code")
				for item in result.get("candidates", [])],
		})
		return result

	async def fundamental_node(state):
		await progress("fundamental", "Reading latest local prices")
		result = await fundamental_agent.run(state)
		await progress("fundamental", "Live price analysis complete", {
			"analysis": result.get("fundamental_analysis", []),
		})
		return result

	async def technical_node(state):
		await progress("technical", "Loading historical candles and indicators")
		result = await technical_agent.run(state)
		await progress("technical", "Technical analysis complete", {
			"analysis": result.get("technical_analysis", []),
		})
		return result

	async def scoring_node(state):
		await progress("scoring", "Ranking the shortlisted stocks")
		result = await scoring_agent.run(state)
		await progress("scoring", "Ranking complete", {"ranking": result.get("ranking", [])})
		return result

	workflow = StateGraph(InvestmentState)
	workflow.add_node("news_search", news_search_node)
	workflow.add_node("market_data", market_data_node)
	workflow.add_node("universe", universe_node)
	workflow.add_node("fundamental", fundamental_node)
	workflow.add_node("technical", technical_node)
	workflow.add_node("scoring", scoring_node)
	workflow.add_edge(START, "news_search")
	workflow.add_edge("news_search", "market_data")
	workflow.add_edge("market_data", "universe")
	workflow.add_edge("universe", "fundamental")
	workflow.add_edge("fundamental", "technical")
	workflow.add_edge("technical", "scoring")
	workflow.add_edge("scoring", END)
	return workflow.compile()


async def run_research(state: dict, on_progress: ProgressCallback | None = None) -> dict:
	"""Run the compiled LangGraph research workflow."""
	state.setdefault("market", "US")
	state.setdefault("universe", "equity")
	state.setdefault("errors", [])
	state.setdefault("evidence", [])
	state.setdefault("fundamental_analysis", [])
	state.setdefault("technical_analysis", [])
	state.setdefault("risk_analysis", [])
	state.setdefault("analyses", [])
	state.setdefault("research_urls", [])
	state.setdefault("max_candidates", 10)
	state.setdefault("news_results", [])
	state["market"] = get_market(state["market"]).code
	result = await build_workflow(on_progress).ainvoke(state)
	if on_progress is not None:
		await on_progress("complete", "Research completed", None)
	return result
