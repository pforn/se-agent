from unittest.mock import MagicMock, patch

import pytest

from src.kb.indexer import (
    index_competitive_intel,
    index_discovery_summary,
    index_meeting_notes,
    index_product_feedback,
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


class TestIndexMeetingNotes:
    def test_indexes_to_meeting_notes_collection(self, mock_store, base_state):
        summary = "Met with Acme Corp. Discussed Snowflake migration timeline."
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_meeting_notes(base_state, summary)

        mock_store.add_document.assert_called_once()
        call = mock_store.add_document.call_args
        assert call.kwargs["collection_name"] == "meeting_notes"
        assert call.kwargs["text"] == summary
        assert call.kwargs["metadata"]["customer_id"] == "acme-corp"
        assert call.kwargs["metadata"]["customer_name"] == "Acme Corp"
        assert call.kwargs["metadata"]["cloud_provider"] == "aws"

    def test_doc_id_includes_customer_id_and_index(self, mock_store, base_state):
        base_state["meeting_summaries"] = [{"type": "a"}, {"type": "b"}, {"type": "c"}]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_meeting_notes(base_state, "notes text")

        call = mock_store.add_document.call_args
        assert "acme-corp" in call.kwargs["doc_id"]
        assert "3" in call.kwargs["doc_id"]

    def test_uses_meeting_count_zero_when_no_summaries(self, mock_store, base_state):
        base_state["meeting_summaries"] = []
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_meeting_notes(base_state, "first meeting")

        call = mock_store.add_document.call_args
        assert "0" in call.kwargs["doc_id"]


class TestIndexProductFeedback:
    def test_indexes_each_feedback_item_separately(self, mock_store, base_state):
        base_state["product_feedback"] = [
            {
                "feature_area": "dbt integration",
                "description": "Need dbt-core 1.8 support",
                "customer": "Acme Corp",
                "severity": "blocker",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
            {
                "feature_area": "security",
                "description": "SOC2 Type II certification needed",
                "customer": "Acme Corp",
                "severity": "important",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_product_feedback(base_state)

        assert mock_store.add_document.call_count == 2

    def test_feedback_metadata_includes_severity_and_area(self, mock_store, base_state):
        base_state["product_feedback"] = [
            {
                "feature_area": "dbt integration",
                "description": "Need dbt-core 1.8 support",
                "customer": "Acme Corp",
                "severity": "blocker",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_product_feedback(base_state)

        call = mock_store.add_document.call_args
        assert call.kwargs["metadata"]["severity"] == "blocker"
        assert call.kwargs["metadata"]["feature_area"] == "dbt integration"
        assert call.kwargs["collection_name"] == "competitive_intel"

    def test_feedback_text_includes_description(self, mock_store, base_state):
        base_state["product_feedback"] = [
            {
                "feature_area": "security",
                "description": "SOC2 Type II certification needed",
                "customer": "Acme Corp",
                "severity": "important",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_product_feedback(base_state)

        call = mock_store.add_document.call_args
        assert "SOC2 Type II certification needed" in call.kwargs["text"]
        assert "security" in call.kwargs["text"]

    def test_skips_if_no_product_feedback(self, mock_store, base_state):
        base_state["product_feedback"] = []
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_product_feedback(base_state)

        mock_store.add_document.assert_not_called()


class TestIndexCompetitiveIntel:
    def test_indexes_each_item_separately(self, mock_store, base_state):
        base_state["competitive_intel"] = [
            {
                "competitor": "Snowflake",
                "claim": "Better price-performance on Iceberg tables",
                "tower_response": "Tower is serverless and avoids warehouse idle costs",
                "source": "https://example.com/comparison",
                "created_at": "2026-03-18T00:00:00Z",
            },
            {
                "competitor": "Databricks",
                "claim": "Delta UniForm provides Iceberg compatibility",
                "tower_response": "Native Iceberg avoids format translation overhead",
                "source": "Tavily research",
                "created_at": "2026-03-18T00:00:00Z",
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_competitive_intel(base_state)

        assert mock_store.add_document.call_count == 2

    def test_metadata_includes_competitor(self, mock_store, base_state):
        base_state["competitive_intel"] = [
            {
                "competitor": "Snowflake",
                "claim": "Better performance",
                "tower_response": "Serverless advantage",
                "source": "web",
                "created_at": "2026-03-18T00:00:00Z",
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_competitive_intel(base_state)

        call = mock_store.add_document.call_args
        assert call.kwargs["collection_name"] == "competitive_intel"
        assert call.kwargs["metadata"]["competitor"] == "Snowflake"
        assert call.kwargs["metadata"]["customer_id"] == "acme-corp"

    def test_text_includes_claim_and_response(self, mock_store, base_state):
        base_state["competitive_intel"] = [
            {
                "competitor": "Snowflake",
                "claim": "Lower cost per query",
                "tower_response": "Serverless eliminates idle compute",
                "source": "analysis",
                "created_at": "2026-03-18T00:00:00Z",
            },
        ]
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_competitive_intel(base_state)

        call = mock_store.add_document.call_args
        assert "Lower cost per query" in call.kwargs["text"]
        assert "Serverless eliminates idle compute" in call.kwargs["text"]

    def test_skips_if_no_competitive_intel(self, mock_store, base_state):
        base_state["competitive_intel"] = []
        with patch("src.kb.indexer.get_kb_store", return_value=mock_store):
            index_competitive_intel(base_state)

        mock_store.add_document.assert_not_called()
