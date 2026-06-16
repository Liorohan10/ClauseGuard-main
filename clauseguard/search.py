import logging
import asyncio
from tavily import TavilyClient
from clauseguard.config import settings

logger = logging.getLogger(__name__)

# List of strictly allowed authoritative domains
AUTHORITATIVE_DOMAINS = [
    "gdpr-info.eu",
    "www.edpb.europa.eu",
    "www.legislation.gov.au",
    "edpb.europa.eu",
    "legislation.gov.au"
]

def tavily_search(query: str, api_key: str | None = None) -> list[dict]:
    """
    Perform a web search using Tavily, strictly restricted to authoritative domains.
    Returns a list of search result items containing title, url, content, and raw score.
    """
    key = api_key or settings.tavily_api_key
    if not key:
        logger.warning("TAVILY_API_KEY is not set. Tavily search will return empty results.")
        return []
    
    try:
        client = TavilyClient(api_key=key)
        # Restrict the domains strictly using include_domains
        response = client.search(
            query=query,
            include_domains=AUTHORITATIVE_DOMAINS,
            search_depth="advanced",
            max_results=5
        )
        return response.get("results", [])
    except Exception as e:
        logger.exception("Tavily search failed for query: %s", query)
        return []

async def tavily_search_async(query: str, api_key: str | None = None) -> list[dict]:
    """
    Asynchronous wrapper for tavily_search, executed in an event loop thread pool.
    """
    return await asyncio.to_thread(tavily_search, query, api_key)
