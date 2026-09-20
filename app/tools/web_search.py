from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup


async def search_web(query: str, limit: int = 10) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "stock-research-agent/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result")[:limit]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if link and link.get("href"):
            results.append({"title": link.get_text(" ", strip=True),
                            "url": link["href"],
                            "snippet": snippet.get_text(" ", strip=True) if snippet else ""})
    return results
