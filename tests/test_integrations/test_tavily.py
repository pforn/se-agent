from unittest.mock import MagicMock, patch

import pytest

from src.integrations.tavily_search import TavilySearchClient, get_tavily_client


class TestTavilySearchClient:
    def test_search_returns_structured_results(self):
        mock_inner = MagicMock()
        mock_inner.search.return_value = {
            "results": [
                {
                    "title": "Snowflake vs Tower comparison",
                    "url": "https://example.com/comparison",
                    "content": "Tower offers serverless Iceberg-native compute...",
                    "score": 0.95,
                },
                {
                    "title": "Data platform benchmarks 2026",
                    "url": "https://example.com/benchmarks",
                    "content": "In our testing, Tower outperformed Snowflake on...",
                    "score": 0.88,
                },
            ]
        }

        client = TavilySearchClient(inner_client=mock_inner)
        results = client.search("Snowflake vs Tower data platform")

        assert len(results) == 2
        assert results[0]["title"] == "Snowflake vs Tower comparison"
        assert results[0]["url"] == "https://example.com/comparison"
        assert "content" in results[0]
        assert "score" in results[0]

    def test_search_respects_max_results(self):
        mock_inner = MagicMock()
        mock_inner.search.return_value = {"results": []}

        client = TavilySearchClient(inner_client=mock_inner)
        client.search("test query", max_results=3)

        call_kwargs = mock_inner.search.call_args
        assert call_kwargs[1]["max_results"] == 3

    def test_search_handles_api_error(self):
        mock_inner = MagicMock()
        mock_inner.search.side_effect = Exception("API rate limit exceeded")

        client = TavilySearchClient(inner_client=mock_inner)
        results = client.search("test query")

        assert results == []

    def test_search_handles_empty_results(self):
        mock_inner = MagicMock()
        mock_inner.search.return_value = {"results": []}

        client = TavilySearchClient(inner_client=mock_inner)
        results = client.search("obscure query")

        assert results == []


class TestGetTavilyClient:
    def test_returns_none_when_no_api_key(self):
        with patch("src.integrations.tavily_search.settings") as mock_settings:
            mock_settings.tavily_api_key = ""
            with patch("src.integrations.tavily_search._tavily_client", None):
                client = get_tavily_client()
            assert client is None

    def test_returns_client_when_api_key_set(self):
        with (
            patch("src.integrations.tavily_search.settings") as mock_settings,
            patch("src.integrations.tavily_search.TavilyClient") as mock_tavily_cls,
            patch("src.integrations.tavily_search._tavily_client", None),
        ):
            mock_settings.tavily_api_key = "tvly-test-key"
            mock_tavily_cls.return_value = MagicMock()
            client = get_tavily_client()
            assert client is not None

    def test_returns_none_when_import_fails(self):
        with (
            patch("src.integrations.tavily_search.settings") as mock_settings,
            patch("src.integrations.tavily_search.TavilyClient", side_effect=Exception("import error")),
            patch("src.integrations.tavily_search._tavily_client", None),
        ):
            mock_settings.tavily_api_key = "tvly-test-key"
            client = get_tavily_client()
            assert client is None
