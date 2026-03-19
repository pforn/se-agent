import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.poc.design_architecture import design_architecture
from src.graph.poc.generate_poc_plan import generate_poc_plan
from src.graph.poc.competitive_positioning import competitive_positioning
from src.graph.poc.create_demo_script import create_demo_script


POC_SCOPING_MESSAGE = (
    "Scope: Migrate 'orders' pipeline (PostgreSQL CDC → S3 → Snowflake → dbt → BI)\n"
    "Target: PostgreSQL CDC → S3 → Tower (Iceberg) → dbt → Trino for BI\n"
    "Success criteria: dbt models run on Tower, Trino within 2x Snowflake perf, "
    "Spark reads same tables, pipeline under 30 min\n"
    "Timeline: 2 weeks. Jordan + 2 ICs available."
)


@pytest.fixture
def base_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "poc",
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "cloud_provider": "aws",
            "compute_engines": ["dbt-core 1.8", "Spark 3.5"],
            "data_volume_tb": 80.0,
            "pain_points": ["Snowflake costs 3x YoY"],
        },
        "use_cases": [
            {
                "name": "Analytics Migration",
                "description": "Migrate analytics from Snowflake to Tower",
                "data_sources": ["postgres", "s3"],
                "target_consumers": ["Looker"],
                "latency_requirement": "batch daily",
                "current_solution": "Snowflake",
                "tower_fit": "strong",
                "notes": "",
            }
        ],
        "stakeholders": [
            {"name": "Jordan Chen", "role": "Head of Data Eng",
             "influence": "champion", "sentiment": "positive", "notes": "Technical lead"},
            {"name": "Sarah Kim", "role": "VP Eng",
             "influence": "evaluator", "sentiment": "neutral", "notes": "Budget owner"},
        ],
        "metrics": "Cost savings",
        "economic_buyer": "Sarah Kim",
        "decision_criteria": ["TCO", "migration effort", "query performance"],
        "decision_process": "PoC then executive review",
        "identified_pain": ["Snowflake costs 3x YoY"],
        "champion": "Jordan Chen",
        "health_score": 75,
        "messages": [HumanMessage(content=POC_SCOPING_MESSAGE)],
        "action_items": [],
        "product_feedback": [],
        "competitive_intel": [],
        "meeting_summaries": [
            {
                "type": "stack_analysis",
                "content": {
                    "stack_assessment": "AWS-based Snowflake shop with dbt.",
                    "tower_fit_analysis": "Strong fit for migration.",
                    "risk_factors": ["dbt 1.8 adapter in beta"],
                    "relevant_patterns": ["Snowflake → Tower migration"],
                    "recommended_approach": "Start with analytics pipeline PoC.",
                },
            }
        ],
        "generated_docs": [],
        "pending_approval": None,
        "last_node": None,
        "error": None,
        "created_at": "2026-03-19T00:00:00Z",
        "updated_at": "2026-03-19T00:00:00Z",
    }


@pytest.fixture
def mock_llm_response():
    def _make(content: str | dict | list):
        if isinstance(content, (dict, list)):
            content = json.dumps(content)
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(content=content))
        return mock
    return _make


# --- design_architecture tests ---

class TestDesignArchitecture:
    ARCH_OUTPUT = {
        "component_mapping": [
            {"current": "Snowflake", "target": "Tower (Iceberg)", "action": "replace"},
            {"current": "dbt-core 1.8", "target": "dbt-core 1.8 on Tower", "action": "migrate"},
        ],
        "data_flow_description": "PostgreSQL CDC → S3 → Tower Iceberg → dbt → Trino",
        "migration_steps": ["Set up Tower catalog", "Configure Iceberg tables", "Migrate dbt models"],
        "tower_configuration": "Single catalog, date-partitioned orders table",
        "integration_points": ["Spark 3.5 reads Iceberg", "Looker via Trino"],
        "risk_mitigations": ["dbt 1.8 adapter: pin to stable version"],
        "architecture_summary": "Tower replaces Snowflake as the primary warehouse...",
    }

    @pytest.mark.asyncio
    async def test_produces_architecture_doc(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_OUTPUT)

        with (
            patch("src.graph.poc.design_architecture.get_llm", return_value=mock),
            patch("src.graph.poc.design_architecture.interrupt", return_value={"action": "approve"}),
        ):
            result = await design_architecture(base_state)

        assert result["last_node"] == "design_architecture"
        assert len(result["meeting_summaries"]) == 2
        arch_summary = next(s for s in result["meeting_summaries"] if s["type"] == "poc_architecture")
        assert "component_mapping" in arch_summary["content"]

    @pytest.mark.asyncio
    async def test_appends_to_generated_docs(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_OUTPUT)

        with (
            patch("src.graph.poc.design_architecture.get_llm", return_value=mock),
            patch("src.graph.poc.design_architecture.interrupt", return_value={"action": "approve"}),
        ):
            result = await design_architecture(base_state)

        assert len(result["generated_docs"]) == 1
        assert result["generated_docs"][0]["type"] == "poc_architecture"

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        revised = {**self.ARCH_OUTPUT, "architecture_summary": "Revised architecture..."}
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=json.dumps(self.ARCH_OUTPUT)),
                         AIMessage(content=json.dumps(revised))]
        )

        with (
            patch("src.graph.poc.design_architecture.get_llm", return_value=mock),
            patch("src.graph.poc.design_architecture.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Add more detail on Spark integration"},
                      {"action": "approve"},
                  ]),
        ):
            result = await design_architecture(base_state)

        assert mock.ainvoke.call_count == 2
        assert result["generated_docs"][0]["type"] == "poc_architecture"

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_OUTPUT)

        with (
            patch("src.graph.poc.design_architecture.get_llm", return_value=mock),
            patch("src.graph.poc.design_architecture.interrupt", return_value={"action": "reject"}),
        ):
            result = await design_architecture(base_state)

        assert result.get("error") is not None
        assert result["last_node"] == "design_architecture"

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_OUTPUT)

        with (
            patch("src.graph.poc.design_architecture.get_llm", return_value=mock) as mock_get,
            patch("src.graph.poc.design_architecture.interrupt", return_value={"action": "approve"}),
        ):
            await design_architecture(base_state)

        mock_get.assert_called_once_with("strong")


# --- generate_poc_plan tests ---

class TestGeneratePocPlan:
    POC_PLAN_OUTPUT = {
        "scope": {
            "pipelines": ["orders pipeline"],
            "data_sources": ["PostgreSQL", "S3"],
            "outputs": ["Trino BI queries", "Spark ML reads"],
        },
        "success_criteria": [
            "dbt models run on Tower-managed Iceberg tables",
            "Trino query performance within 2x of Snowflake",
        ],
        "timeline": [
            {"week": 1, "goals": ["Environment setup", "Table creation", "CDC config"]},
            {"week": 2, "goals": ["dbt migration", "Performance testing", "Demo"]},
        ],
        "resources": ["Jordan Chen (lead)", "Lisa Zhang (data eng)", "Raj Gupta (ML eng)"],
        "data_requirements": ["orders table (~50GB subset)", "PostgreSQL CDC access"],
        "technical_setup": ["Provision Tower environment", "Configure S3 access"],
        "demo_checkpoints": ["End of week 1: raw data flowing", "End of week 2: full pipeline"],
        "risks": [{"risk": "dbt 1.8 compatibility", "mitigation": "Pin to stable adapter version"}],
        "poc_summary": "Two-week PoC migrating the orders analytics pipeline...",
    }

    @pytest.mark.asyncio
    async def test_produces_poc_plan(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "Tower arch..."}}
        )
        mock = mock_llm_response(self.POC_PLAN_OUTPUT)

        with (
            patch("src.graph.poc.generate_poc_plan.get_llm", return_value=mock),
            patch("src.graph.poc.generate_poc_plan.interrupt", return_value={"action": "approve"}),
        ):
            result = await generate_poc_plan(base_state)

        assert result["last_node"] == "generate_poc_plan"
        assert len(result["generated_docs"]) == 1
        assert result["generated_docs"][0]["type"] == "poc_plan"

    @pytest.mark.asyncio
    async def test_uses_latest_message_as_requirements(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.POC_PLAN_OUTPUT)

        with (
            patch("src.graph.poc.generate_poc_plan.get_llm", return_value=mock),
            patch("src.graph.poc.generate_poc_plan.interrupt", return_value={"action": "approve"}),
        ):
            await generate_poc_plan(base_state)

        prompt_text = mock.ainvoke.call_args[0][0][1].content
        assert "orders" in prompt_text.lower() or "pipeline" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.POC_PLAN_OUTPUT)

        with (
            patch("src.graph.poc.generate_poc_plan.get_llm", return_value=mock),
            patch("src.graph.poc.generate_poc_plan.interrupt", return_value={"action": "reject"}),
        ):
            result = await generate_poc_plan(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.POC_PLAN_OUTPUT)

        with (
            patch("src.graph.poc.generate_poc_plan.get_llm", return_value=mock) as mock_get,
            patch("src.graph.poc.generate_poc_plan.interrupt", return_value={"action": "approve"}),
        ):
            await generate_poc_plan(base_state)

        mock_get.assert_called_once_with("strong")


# --- competitive_positioning tests ---

class TestCompetitivePositioning:
    COMPETITIVE_OUTPUT = {
        "comparison_matrix": [
            {"dimension": "TCO", "tower": "Serverless, pay-per-query", "competitor": "Warehouse credits", "winner": "Tower"},
            {"dimension": "Iceberg support", "tower": "Native", "competitor": "Via UniForm", "winner": "Tower"},
        ],
        "tco_analysis": "At 80TB, Tower saves ~40% vs Snowflake Enterprise.",
        "migration_comparison": "Tower migration is simpler for Iceberg-native workloads.",
        "iceberg_comparison": "Tower has native partition evolution; Snowflake requires manual steps.",
        "ecosystem_fit": "Both support dbt. Tower has native Trino and Spark integration.",
        "references": ["DataCo migrated 100TB from Snowflake to Tower in 3 weeks"],
        "talking_points": [
            "Tower eliminates warehouse idle costs",
            "Native Iceberg means no format translation",
        ],
        "competitive_intel_items": [
            {
                "competitor": "Snowflake",
                "claim": "Lower TCO at scale with serverless Iceberg",
                "tower_response": "Pay-per-query eliminates idle warehouse costs",
                "source": "Tavily research",
            }
        ],
    }

    @pytest.mark.asyncio
    async def test_produces_competitive_doc(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)
        mock_tavily = MagicMock()
        mock_tavily.search.return_value = [
            {"title": "Snowflake vs alternatives", "url": "https://example.com",
             "content": "Comparison article...", "score": 0.9}
        ]

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock),
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=mock_tavily),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
            patch("src.graph.poc.competitive_positioning.index_competitive_intel"),
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            result = await competitive_positioning(base_state)

        assert result["last_node"] == "competitive_positioning"
        assert len(result["generated_docs"]) == 1
        assert result["generated_docs"][0]["type"] == "competitive_positioning"

    @pytest.mark.asyncio
    async def test_populates_competitive_intel(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock),
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=None),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
            patch("src.graph.poc.competitive_positioning.index_competitive_intel"),
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            result = await competitive_positioning(base_state)

        assert len(result["competitive_intel"]) == 1
        assert result["competitive_intel"][0]["competitor"] == "Snowflake"

    @pytest.mark.asyncio
    async def test_indexes_on_approve(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock),
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=None),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
            patch("src.graph.poc.competitive_positioning.index_competitive_intel") as mock_index,
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            await competitive_positioning(base_state)

        mock_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_without_tavily(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock),
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=None),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
            patch("src.graph.poc.competitive_positioning.index_competitive_intel"),
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            result = await competitive_positioning(base_state)

        assert result["last_node"] == "competitive_positioning"

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock),
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "reject"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=None),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            result = await competitive_positioning(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.COMPETITIVE_OUTPUT)

        with (
            patch("src.graph.poc.competitive_positioning.get_llm", return_value=mock) as mock_get,
            patch("src.graph.poc.competitive_positioning.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.competitive_positioning.get_tavily_client", return_value=None),
            patch("src.graph.poc.competitive_positioning.get_kb_store") as mock_kb,
            patch("src.graph.poc.competitive_positioning.index_competitive_intel"),
        ):
            mock_kb.return_value.retrieve_similar.return_value = []
            await competitive_positioning(base_state)

        mock_get.assert_called_once_with("strong")


# --- create_demo_script tests ---

class TestCreateDemoScript:
    DEMO_SCRIPT = (
        "# Tower PoC Demo — Acme Corp\n\n"
        "## Opening\n"
        "Today we'll walk through the orders pipeline migration...\n\n"
        "## Step 1: Iceberg Table Setup\n"
        "```sql\nCREATE TABLE orders USING iceberg...\n```\n\n"
        "## Step 2: dbt Model Execution\n"
        "```bash\ndbt run --select orders_daily\n```\n\n"
        "## Q&A Prep\n"
        "- Jordan (champion): 'How does partition evolution work?'\n"
        "- Sarah (budget): 'What's the TCO comparison?'\n"
    )

    @pytest.mark.asyncio
    async def test_produces_demo_script(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "Tower arch..."}}
        )
        base_state["generated_docs"] = [
            {"type": "poc_plan", "content": json.dumps({"scope": {"pipelines": ["orders"]}})}
        ]
        mock = mock_llm_response(self.DEMO_SCRIPT)

        with (
            patch("src.graph.poc.create_demo_script.get_llm", return_value=mock),
            patch("src.graph.poc.create_demo_script.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.create_demo_script.get_gdrive_client", return_value=None),
        ):
            result = await create_demo_script(base_state)

        assert result["last_node"] == "create_demo_script"
        docs = result["generated_docs"]
        demo_doc = next(d for d in docs if d["type"] == "demo_script")
        assert "Tower PoC Demo" in demo_doc["content"]

    @pytest.mark.asyncio
    async def test_uploads_to_gdrive_when_available(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.DEMO_SCRIPT)
        mock_gdrive = MagicMock()
        mock_gdrive.create_doc.return_value = "https://docs.google.com/document/d/abc/edit"

        with (
            patch("src.graph.poc.create_demo_script.get_llm", return_value=mock),
            patch("src.graph.poc.create_demo_script.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.create_demo_script.get_gdrive_client", return_value=mock_gdrive),
        ):
            result = await create_demo_script(base_state)

        mock_gdrive.create_doc.assert_called_once()
        demo_doc = next(d for d in result["generated_docs"] if d["type"] == "demo_script")
        assert demo_doc["gdrive_url"] == "https://docs.google.com/document/d/abc/edit"

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        original = self.DEMO_SCRIPT
        revised = "# Revised Demo Script\n\nUpdated walkthrough..."
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=original), AIMessage(content=revised)]
        )

        with (
            patch("src.graph.poc.create_demo_script.get_llm", return_value=mock),
            patch("src.graph.poc.create_demo_script.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Add more Spark examples"},
                      {"action": "approve"},
                  ]),
            patch("src.graph.poc.create_demo_script.get_gdrive_client", return_value=None),
        ):
            result = await create_demo_script(base_state)

        assert mock.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.DEMO_SCRIPT)

        with (
            patch("src.graph.poc.create_demo_script.get_llm", return_value=mock),
            patch("src.graph.poc.create_demo_script.interrupt", return_value={"action": "reject"}),
        ):
            result = await create_demo_script(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        base_state["meeting_summaries"].append(
            {"type": "poc_architecture", "content": {"architecture_summary": "arch..."}}
        )
        mock = mock_llm_response(self.DEMO_SCRIPT)

        with (
            patch("src.graph.poc.create_demo_script.get_llm", return_value=mock) as mock_get,
            patch("src.graph.poc.create_demo_script.interrupt", return_value={"action": "approve"}),
            patch("src.graph.poc.create_demo_script.get_gdrive_client", return_value=None),
        ):
            await create_demo_script(base_state)

        mock_get.assert_called_once_with("strong")
