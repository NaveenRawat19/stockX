from app.agents.data_research import DataResearchAgent


async def web_research_agent(state: dict) -> dict:
    """Compatibility entry point for the data research agent."""
    return await DataResearchAgent().run(state)
