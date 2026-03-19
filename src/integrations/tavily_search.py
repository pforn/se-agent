from __future__ import annotations

import logging

from tavily import TavilyClient

from src.config import settings

logger = logging.getLogger(__name__)

_tavily_client: TavilySearchClient | None = None


class TavilySearchClient:
    def __init__(self, inner_client: TavilyClient) -> None:
        self._client = inner_client

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            response = self._client.search(query=query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                }
                for r in response.get("results", [])
            ]
        except Exception:
            logger.warning("Tavily search failed", exc_info=True)
            return []


def get_tavily_client() -> TavilySearchClient | None:
    global _tavily_client
    if _tavily_client is not None:
        return _tavily_client

    if not settings.tavily_api_key:
        logger.debug("No Tavily API key configured, skipping web research")
        return None

    try:
        inner = TavilyClient(api_key=settings.tavily_api_key)
        _tavily_client = TavilySearchClient(inner_client=inner)
        return _tavily_client
    except Exception:
        logger.warning("Failed to initialize Tavily client", exc_info=True)
        return None
