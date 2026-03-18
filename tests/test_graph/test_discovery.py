import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.discovery.gather_context import gather_context
from src.graph.discovery.analyze_stack import analyze_stack


@pytest.fixture
def base_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "discovery",
        "tech_env": {},
        "use_cases": [],
        "stakeholders": [],
        "metrics": None,
        "economic_buyer": None,
        "decision_criteria": [],
        "decision_process": None,
        "identified_pain": [],
        "champion": None,
        "health_score": None,
        "messages": [HumanMessage(content="We run Snowflake Enterprise on AWS with 80TB, dbt-core 1.8, Airflow 2.9.")],
        "action_items": [],
        "product_feedback": [],
        "competitive_intel": [],
        "meeting_summaries": [],
        "generated_docs": [],
        "pending_approval": None,
        "last_node": None,
        "error": None,
        "created_at": "2026-03-16T00:00:00Z",
        "updated_at": "2026-03-16T00:00:00Z",
    }


@pytest.fixture
def mock_llm_response():
    def _make(content: str | dict):
        if isinstance(content, dict):
            content = json.dumps(content)
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(content=content))
        return mock
    return _make


@pytest.fixture
def mock_kb_store():
    store = MagicMock()
    store.retrieve_similar = MagicMock(return_value=[])
    store.add_document = MagicMock()
    return store


@pytest.mark.asyncio
async def test_gather_context_extracts_tech_env(base_state, mock_llm_response):
    llm_output = {
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "compute_engines": ["dbt-core 1.8", "Spark 3.5"],
            "cloud_provider": "aws",
            "data_volume_tb": 80.0,
            "pain_points": ["Snowflake costs 3x YoY"],
        },
        "stakeholders": [
            {"name": "Jordan Chen", "role": "Head of Data Engineering",
             "influence": "champion", "sentiment": "positive", "notes": "Technical lead"}
        ],
    }
    mock = mock_llm_response(llm_output)

    with patch("src.graph.discovery.gather_context.get_llm", return_value=mock):
        result = await gather_context(base_state)

    assert result["tech_env"]["current_warehouse"] == "Snowflake Enterprise"
    assert result["tech_env"]["cloud_provider"] == "aws"
    assert len(result["stakeholders"]) == 1
    assert result["stakeholders"][0]["name"] == "Jordan Chen"
    assert result["last_node"] == "gather_context"


@pytest.mark.asyncio
async def test_gather_context_merges_existing(base_state, mock_llm_response):
    base_state["tech_env"] = {"current_warehouse": "Snowflake Enterprise", "cloud_provider": "aws"}
    base_state["stakeholders"] = [
        {"name": "Jordan Chen", "role": "Head of Data Eng", "influence": "champion",
         "sentiment": "positive", "notes": "Existing"}
    ]

    llm_output = {
        "tech_env": {"data_volume_tb": 80.0, "orchestrator": "Airflow 2.9"},
        "stakeholders": [
            {"name": "Jordan Chen", "role": "Head of Data Eng", "influence": "champion",
             "sentiment": "positive", "notes": "Updated"},
            {"name": "Sarah Kim", "role": "VP Eng", "influence": "evaluator",
             "sentiment": "neutral", "notes": "Budget owner"},
        ],
    }
    mock = mock_llm_response(llm_output)

    with patch("src.graph.discovery.gather_context.get_llm", return_value=mock):
        result = await gather_context(base_state)

    assert result["tech_env"]["current_warehouse"] == "Snowflake Enterprise"
    assert result["tech_env"]["data_volume_tb"] == 80.0
    assert result["tech_env"]["orchestrator"] == "Airflow 2.9"
    assert len(result["stakeholders"]) == 2


@pytest.mark.asyncio
async def test_analyze_stack_produces_meeting_summary(base_state, mock_llm_response, mock_kb_store):
    base_state["tech_env"] = {
        "current_warehouse": "Snowflake Enterprise",
        "cloud_provider": "aws",
        "compute_engines": ["dbt-core 1.8"],
    }

    llm_output = {
        "stack_assessment": "AWS-based Snowflake shop with dbt.",
        "tower_fit_analysis": "Strong fit for migration.",
        "risk_factors": ["dbt 1.8 adapter in beta"],
        "relevant_patterns": ["Snowflake → Tower migration"],
        "recommended_approach": "Start with analytics pipeline PoC.",
    }
    mock = mock_llm_response(llm_output)

    with (
        patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock),
        patch("src.graph.discovery.analyze_stack.get_kb_store", return_value=mock_kb_store),
        patch("src.graph.discovery.analyze_stack._index_sa"),
    ):
        result = await analyze_stack(base_state)

    assert result["last_node"] == "analyze_stack"
    summaries = result["meeting_summaries"]
    assert len(summaries) == 1
    assert summaries[0]["type"] == "stack_analysis"
    assert "stack_assessment" in summaries[0]["content"]


@pytest.mark.asyncio
async def test_analyze_stack_queries_kb_with_cloud_filter(base_state, mock_llm_response, mock_kb_store):
    base_state["tech_env"] = {
        "current_warehouse": "Snowflake Enterprise",
        "cloud_provider": "aws",
    }
    mock = mock_llm_response({"stack_assessment": "test", "tower_fit_analysis": "test",
                              "risk_factors": [], "relevant_patterns": [], "recommended_approach": "test"})

    with (
        patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock),
        patch("src.graph.discovery.analyze_stack.get_kb_store", return_value=mock_kb_store),
        patch("src.graph.discovery.analyze_stack._index_sa"),
    ):
        await analyze_stack(base_state)

    calls = mock_kb_store.retrieve_similar.call_args_list
    assert len(calls) == 2
    # stack_analyses call should have cloud_provider filter
    assert calls[0].args[0] == "stack_analyses"
    assert calls[0].kwargs["where"] == {"cloud_provider": "aws"}
    # discovery_summaries call — no filter
    assert calls[1].args[0] == "discovery_summaries"


@pytest.mark.asyncio
async def test_analyze_stack_injects_similar_contexts(base_state, mock_llm_response, mock_kb_store):
    base_state["tech_env"] = {
        "current_warehouse": "Databricks",
        "cloud_provider": "gcp",
    }

    mock_kb_store.retrieve_similar.side_effect = [
        [{"id": "sa:prev", "text": "Previous GCP analysis", "metadata": {"customer_name": "PrevCo"}, "distance": 0.2}],
        [],
    ]

    mock = mock_llm_response({"stack_assessment": "test", "tower_fit_analysis": "test",
                              "risk_factors": [], "relevant_patterns": [], "recommended_approach": "test"})

    with (
        patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock),
        patch("src.graph.discovery.analyze_stack.get_kb_store", return_value=mock_kb_store),
        patch("src.graph.discovery.analyze_stack._index_sa"),
    ):
        await analyze_stack(base_state)

    llm_call = mock.ainvoke.call_args[0][0]
    prompt_text = llm_call[1].content
    assert "PrevCo" in prompt_text
    assert "Previous GCP analysis" in prompt_text


@pytest.mark.asyncio
async def test_analyze_stack_indexes_result(base_state, mock_llm_response, mock_kb_store):
    base_state["tech_env"] = {"current_warehouse": "Snowflake", "cloud_provider": "aws"}

    llm_output = {"stack_assessment": "test", "tower_fit_analysis": "test",
                  "risk_factors": [], "relevant_patterns": [], "recommended_approach": "test"}
    mock = mock_llm_response(llm_output)

    with (
        patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock),
        patch("src.graph.discovery.analyze_stack.get_kb_store", return_value=mock_kb_store),
        patch("src.graph.discovery.analyze_stack._index_sa") as mock_index,
    ):
        await analyze_stack(base_state)

    mock_index.assert_called_once()
    indexed_state = mock_index.call_args[0][0]
    assert indexed_state["last_node"] == "analyze_stack"
    assert any(s["type"] == "stack_analysis" for s in indexed_state["meeting_summaries"])


@pytest.mark.asyncio
async def test_analyze_stack_handles_kb_unavailable(base_state, mock_llm_response):
    """When KB store raises, analyze_stack should still complete."""
    base_state["tech_env"] = {"current_warehouse": "Snowflake", "cloud_provider": "aws"}

    mock = mock_llm_response({"stack_assessment": "test", "tower_fit_analysis": "test",
                              "risk_factors": [], "relevant_patterns": [], "recommended_approach": "test"})

    with (
        patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock),
        patch("src.graph.discovery.analyze_stack.get_kb_store", side_effect=RuntimeError("no KB")),
        patch("src.graph.discovery.analyze_stack._index_sa", side_effect=RuntimeError("no KB")),
    ):
        result = await analyze_stack(base_state)

    assert result["last_node"] == "analyze_stack"
    assert len(result["meeting_summaries"]) == 1
