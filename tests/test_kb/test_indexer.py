from unittest.mock import MagicMock, patch

import pytest

from src.kb.indexer import (
    index_discovery_summary,
    index_stack_analysis,
    index_use_cases,
)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.add_document = MagicMock()
    return store


@pytest.fixture
def base_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "discovery",
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "cloud_provider": "aws",
            "data_volume_tb": 80.0,
        },
        "use_cases": [
            {
                "name": "Analytics Migration",
                "description": "Migrate analytics pipeline from Snowflake to Tower",
                "data_sources": ["postgres", "s3"],
                "target_consumers": ["Looker", "dbt"],
                "latency_requirement": "batch daily",
                "current_solution": "Snowflake",
                "tower_fit": "strong",
                "notes": "Good fit",
            },
            {
                "name": "Real-time Dashboard",
                "description": "Near-real-time dashboards for ops team",
                "data_sources": ["kafka"],
                "target_consumers": ["Grafana"],
                "latency_requirement": "< 5 min",
                "current_solution": None,
                "tower_fit": "moderate",
                "notes": "Micro-batch latency may suffice",
            },
        ],
        "stakeholders": [],
        "meeting_summaries": [
            {
                "type": "stack_analysis",
                "content": {
                    "stack_assessment": "AWS Snowflake shop",
                    "tower_fit_analysis": "Strong fit",
                    "risk_factors": ["dbt 1.8 beta"],
                    "relevant_patterns": ["Snowflake -> Tower"],
                    "recommended_approach": "Start with analytics PoC",
                },
            }
        ],
        "generated_docs": [],
        "updated_at": "2026-03-18T00:00:00Z",
    }


class TestIndexDiscoverySummary:
    def test_indexes_to_discovery_summaries_collection(self, mock_store, base_state):
        doc_content = "# Discovery Summary\n\nAcme Corp is migrating from Snowflake..."
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_discovery_summary(base_state, doc_content)

        mock_store.add_document.assert_called_once()
        call = mock_store.add_document.call_args
        assert call.kwargs["collection_name"] == "discovery_summaries"
        assert call.kwargs["text"] == doc_content
        assert call.kwargs["metadata"]["customer_id"] == "acme-corp"
        assert call.kwargs["metadata"]["customer_name"] == "Acme Corp"
        assert call.kwargs["metadata"]["phase"] == "discovery"
        assert call.kwargs["metadata"]["cloud_provider"] == "aws"

    def test_doc_id_includes_customer_id(self, mock_store, base_state):
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_discovery_summary(base_state, "summary text")

        call = mock_store.add_document.call_args
        assert "acme-corp" in call.kwargs["doc_id"]


class TestIndexStackAnalysis:
    def test_indexes_stack_analysis_from_meeting_summaries(self, mock_store, base_state):
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_stack_analysis(base_state)

        mock_store.add_document.assert_called_once()
        call = mock_store.add_document.call_args
        assert call.kwargs["collection_name"] == "stack_analyses"
        assert "acme-corp" in call.kwargs["doc_id"]
        assert call.kwargs["metadata"]["customer_id"] == "acme-corp"
        assert call.kwargs["metadata"]["cloud_provider"] == "aws"
        text = call.kwargs["text"]
        assert "stack_assessment" in text

    def test_skips_if_no_stack_analysis(self, mock_store, base_state):
        base_state["meeting_summaries"] = []
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_stack_analysis(base_state)

        mock_store.add_document.assert_not_called()


class TestIndexUseCases:
    def test_indexes_each_use_case_separately(self, mock_store, base_state):
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_use_cases(base_state)

        assert mock_store.add_document.call_count == 2

    def test_use_case_metadata_includes_tower_fit(self, mock_store, base_state):
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_use_cases(base_state)

        calls = mock_store.add_document.call_args_list
        first_meta = calls[0].kwargs["metadata"]
        assert first_meta["tower_fit"] == "strong"
        assert first_meta["customer_id"] == "acme-corp"
        second_meta = calls[1].kwargs["metadata"]
        assert second_meta["tower_fit"] == "moderate"

    def test_use_case_text_includes_description(self, mock_store, base_state):
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_use_cases(base_state)

        calls = mock_store.add_document.call_args_list
        assert "Analytics Migration" in calls[0].kwargs["text"]
        assert "Migrate analytics pipeline" in calls[0].kwargs["text"]

    def test_skips_if_no_use_cases(self, mock_store, base_state):
        base_state["use_cases"] = []
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_use_cases(base_state)

        mock_store.add_document.assert_not_called()
