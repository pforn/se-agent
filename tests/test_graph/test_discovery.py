import json
from unittest.mock import AsyncMock, patch

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
    """Returns a factory for mock LLM responses."""
    def _make(content: str | dict):
        if isinstance(content, dict):
            content = json.dumps(content)
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(content=content))
        return mock
    return _make


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
    # Jordan exists, Sarah is new
    assert len(result["stakeholders"]) == 2


@pytest.mark.asyncio
async def test_analyze_stack_produces_meeting_summary(base_state, mock_llm_response):
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

    with patch("src.graph.discovery.analyze_stack.get_llm", return_value=mock):
        result = await analyze_stack(base_state)

    assert result["last_node"] == "analyze_stack"
    summaries = result["meeting_summaries"]
    assert len(summaries) == 1
    assert summaries[0]["type"] == "stack_analysis"
    assert "stack_assessment" in summaries[0]["content"]
