from app.agents.fundamental import fundamental_agent
from app.agents.technical import technical_agent
from app.agents.universe import universe_agent
from app.agents.data_research import DataResearchAgent
from app.agents.news_search import NewsWebSearchAgent
from app.services.scoring import rank_stocks


class WebResearchAgent(DataResearchAgent):
    async def run(self, state: dict) -> dict:
        return await super().run(state)


class NewsAgent(NewsWebSearchAgent):
    pass


class UniverseAgent:
    async def run(self, state: dict) -> dict:
        return await universe_agent(state)


class FundamentalAgent:
    async def run(self, state: dict) -> dict:
        return await fundamental_agent(state)


class TechnicalAgent:
    async def run(self, state: dict) -> dict:
        return await technical_agent(state)


class ScoringAgent:
    async def run(self, state: dict) -> dict:
        return rank_stocks(state)
