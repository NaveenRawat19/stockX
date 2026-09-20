import httpx
from bs4 import BeautifulSoup


async def fetch_page(url: str) -> dict:
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "stock-research-agent/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return {"title": soup.title.get_text(" ", strip=True) if soup.title else url,
            "url": str(response.url),
            "content": " ".join(soup.get_text(" ").split())}
