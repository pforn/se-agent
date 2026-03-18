"""Integration test: real ChromaDB (ephemeral) + real embeddings for index-then-retrieve round-trip."""

from unittest.mock import patch

import pytest

from src.kb.store import KBStore
from src.kb.indexer import index_discovery_summary, index_stack_analysis, index_use_cases


@pytest.fixture
def real_store(tmp_path):
    return KBStore(persist_dir=str(tmp_path / "chromadb_test"))


@pytest.fixture
def sample_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "discovery",
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "cloud_provider": "aws",
            "data_volume_tb": 80.0,
            "compute_engines": ["dbt-core 1.8", "Spark 3.5"],
        },
        "use_cases": [
            {
                "name": "Analytics Migration",
                "description": "Migrate analytics pipeline from Snowflake to Tower for cost savings",
                "data_sources": ["postgres", "s3"],
                "target_consumers": ["Looker", "dbt"],
                "latency_requirement": "batch daily",
                "current_solution": "Snowflake",
                "tower_fit": "strong",
                "notes": "Primary use case, strong fit",
            },
        ],
        "meeting_summaries": [
            {
                "type": "stack_analysis",
                "content": {
                    "stack_assessment": "AWS-based Snowflake Enterprise with dbt-core 1.8 and Spark 3.5",
                    "tower_fit_analysis": "Strong fit for migration, especially analytics workloads",
                    "risk_factors": ["dbt 1.8 adapter in beta"],
                    "relevant_patterns": ["Snowflake to Tower migration"],
                    "recommended_approach": "Start with analytics pipeline PoC",
                },
            }
        ],
        "updated_at": "2026-03-18T00:00:00Z",
    }


class TestIndexThenRetrieve:
    def test_discovery_summary_round_trip(self, real_store, sample_state):
        doc = "# Discovery Summary for Acme Corp\n\nAcme runs Snowflake Enterprise on AWS with 80TB."

        with patch("src.kb.indexer.get_kb_store", return_value=real_store):
            index_discovery_summary(sample_state, doc)

        results = real_store.retrieve_similar(
            "discovery_summaries", "Snowflake AWS migration"
        )
        assert len(results) == 1
        assert "Acme" in results[0]["text"]
        assert results[0]["metadata"]["customer_id"] == "acme-corp"
        assert results[0]["metadata"]["cloud_provider"] == "aws"

    def test_stack_analysis_round_trip(self, real_store, sample_state):
        with patch("src.kb.indexer.get_kb_store", return_value=real_store):
            index_stack_analysis(sample_state)

        results = real_store.retrieve_similar(
            "stack_analyses", "Snowflake dbt migration"
        )
        assert len(results) == 1
        assert "Snowflake Enterprise" in results[0]["text"]

    def test_stack_analysis_metadata_filter(self, real_store, sample_state):
        with patch("src.kb.indexer.get_kb_store", return_value=real_store):
            index_stack_analysis(sample_state)

        aws_results = real_store.retrieve_similar(
            "stack_analyses", "data migration", where={"cloud_provider": "aws"}
        )
        assert len(aws_results) == 1

        gcp_results = real_store.retrieve_similar(
            "stack_analyses", "data migration", where={"cloud_provider": "gcp"}
        )
        assert len(gcp_results) == 0

    def test_use_cases_round_trip(self, real_store, sample_state):
        with patch("src.kb.indexer.get_kb_store", return_value=real_store):
            index_use_cases(sample_state)

        results = real_store.retrieve_similar(
            "use_cases", "analytics pipeline migration"
        )
        assert len(results) == 1
        assert "Analytics Migration" in results[0]["text"]
        assert results[0]["metadata"]["tower_fit"] == "strong"

    def test_cross_customer_retrieval(self, real_store):
        """Index two customers, retrieve the more relevant one."""
        state_a = {
            "customer_id": "alpha-inc",
            "customer_name": "Alpha Inc",
            "phase": "discovery",
            "tech_env": {"cloud_provider": "aws"},
            "use_cases": [],
            "meeting_summaries": [],
            "updated_at": "2026-03-18T00:00:00Z",
        }
        state_b = {
            "customer_id": "beta-co",
            "customer_name": "Beta Co",
            "phase": "discovery",
            "tech_env": {"cloud_provider": "gcp"},
            "use_cases": [],
            "meeting_summaries": [],
            "updated_at": "2026-03-18T00:00:00Z",
        }

        with patch("src.kb.indexer.get_kb_store", return_value=real_store):
            index_discovery_summary(state_a, "Alpha runs Snowflake on AWS with 200TB data warehouse")
            index_discovery_summary(state_b, "Beta uses BigQuery on GCP for ML feature engineering")

        results = real_store.retrieve_similar(
            "discovery_summaries", "BigQuery GCP machine learning"
        )
        assert len(results) == 2
        assert results[0]["metadata"]["customer_id"] == "beta-co"
