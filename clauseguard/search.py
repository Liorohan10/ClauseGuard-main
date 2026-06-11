import asyncio
import logging
import httpx
from typing import Any

from clauseguard.config import settings

logger = logging.getLogger(__name__)

def _ddg_search_sync(query: str, max_results: int) -> list[dict[str, str]]:
    """Synchronous DuckDuckGo search to be run in a background thread."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw_results = ddgs.text(query, max_results=max_results)
            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "content": r.get("body", "")
                })
            return results
    except Exception as e:
        logger.exception("DuckDuckGo search sync call failed")
        return []

async def async_web_search(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Perform an asynchronous web search using Tavily API if configured, falling back to DuckDuckGo."""
    # 1. Tavily Search (if API key provided)
    if settings.tavily_api_key:
        try:
            logger.info("Executing Tavily Search: query=%s", query)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for r in data.get("results", []):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "content": r.get("content", "")
                        })
                    logger.info("Tavily Search successful: found %d results", len(results))
                    return results
                else:
                    logger.error("Tavily Search failed with status %d: %s", response.status_code, response.text)
        except Exception:
            logger.exception("Tavily Search exception occurred, falling back to DDG")

    # 2. DuckDuckGo Search Fallback
    logger.info("Executing DuckDuckGo Search: query=%s", query)
    try:
        results = await asyncio.to_thread(_ddg_search_sync, query, max_results)
        logger.info("DuckDuckGo Search completed: found %d results", len(results))
        return results
    except Exception:
        logger.exception("DuckDuckGo Search exception occurred")
        return []

def format_search_results(results: list[dict[str, str]]) -> str:
    """Format search results into a clean string for LLM prompt context."""
    if not results:
        return "No search results retrieved."
    
    formatted = []
    for idx, r in enumerate(results, 1):
        formatted.append(
            f"Result {idx}: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Snippet/Content: {r['content']}\n"
            "---"
        )
    return "\n\n".join(formatted)
