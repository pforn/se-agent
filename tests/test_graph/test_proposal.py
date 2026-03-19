import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.proposal.draft_proposal import draft_proposal
from src.graph.proposal.add_reference_architecture import add_reference_architecture
from src.graph.proposal.add_deployment_plan import add_deployment_plan
from src.graph.proposal.compile_document import compile_document


@pytest.fixture
def base_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "proposal",
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "cloud_provider": "aws",
            "compute_engines": ["dbt-core 1.8", "Spark 3.5"],
            "data_volume_tb": 80.0,
            "pain_points": ["Snowflake costs 3x YoY", "Vendor lock-in concerns"],
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
        "metrics": "40% cost reduction vs Snowflake",
        "economic_buyer": "Sarah Kim",
        "decision_criteria": ["TCO", "migration effort", "query performance"],
        "decision_process": "PoC then executive review",
        "identified_pain": ["Snowflake costs 3x YoY", "Vendor lock-in"],
        "champion": "Jordan Chen",
        "health_score": 80,
        "messages": [HumanMessage(content="Ready to draft the proposal for Acme Corp.")],
        "action_items": [],
        "product_feedback": [],
        "competitive_intel": [
            {
                "competitor": "Snowflake",
                "claim": "Lower TCO at scale with serverless Iceberg",
                "tower_response": "Pay-per-query eliminates idle warehouse costs",
                "source": "Tavily research",
                "created_at": "2026-03-19T00:00:00Z",
            }
        ],
        "meeting_summaries": [
            {
                "type": "stack_analysis",
                "content": {
                    "stack_assessment": "AWS-based Snowflake shop with dbt.",
                    "tower_fit_analysis": "Strong fit for analytics migration.",
                },
            },
            {
                "type": "poc_architecture",
                "content": {
                    "component_mapping": [
                        {"current": "Snowflake", "target": "Tower (Iceberg)", "action": "replace"},
                    ],
                    "architecture_summary": "Tower replaces Snowflake as primary warehouse.",
                    "data_flow_description": "PostgreSQL CDC → S3 → Tower Iceberg → dbt → Trino",
                },
            },
        ],
        "generated_docs": [
            {
                "type": "discovery_summary",
                "title": "Discovery Summary — Acme Corp",
                "content": "Acme Corp runs Snowflake Enterprise on AWS with 80TB, looking to reduce costs.",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
            {
                "type": "poc_plan",
                "title": "PoC Plan — Acme Corp",
                "content": "Two-week PoC migrating orders analytics pipeline from Snowflake to Tower.",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
            {
                "type": "competitive_positioning",
                "title": "Competitive Positioning — Acme Corp",
                "content": "Tower saves ~40% vs Snowflake Enterprise at 80TB scale.",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
        ],
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


# --- draft_proposal tests ---

class TestDraftProposal:
    PROPOSAL_TEXT = (
        "# Technical Proposal — Acme Corp\n\n"
        "## Executive Summary\n"
        "Acme Corp faces escalating data warehouse costs with Snowflake...\n\n"
        "## Current State & Challenges\n"
        "With 80TB of data and costs growing 3x year-over-year...\n\n"
        "## Proposed Solution\n"
        "Tower's serverless Iceberg platform replaces Snowflake...\n\n"
        "## Expected Outcomes & ROI\n"
        "Estimated 40% cost reduction based on serverless pricing model...\n\n"
        "## Why Tower\n"
        "Native Iceberg support, no vendor lock-in, serverless economics...\n\n"
        "## Engagement Summary\n"
        "Through discovery and PoC, we demonstrated Tower can run Acme's orders pipeline..."
    )

    @pytest.mark.asyncio
    async def test_produces_proposal_doc(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.PROPOSAL_TEXT)

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock),
            patch("src.graph.proposal.draft_proposal.interrupt", return_value={"action": "approve"}),
        ):
            result = await draft_proposal(base_state)

        assert result["last_node"] == "draft_proposal"
        new_docs = result["generated_docs"]
        proposal_doc = next(d for d in new_docs if d["type"] == "proposal_narrative")
        assert "Acme Corp" in proposal_doc["content"]

    @pytest.mark.asyncio
    async def test_appends_to_generated_docs(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.PROPOSAL_TEXT)

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock),
            patch("src.graph.proposal.draft_proposal.interrupt", return_value={"action": "approve"}),
        ):
            result = await draft_proposal(base_state)

        assert len(result["generated_docs"]) == len(base_state["generated_docs"]) + 1

    @pytest.mark.asyncio
    async def test_reads_discovery_and_competitive_context(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.PROPOSAL_TEXT)

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock),
            patch("src.graph.proposal.draft_proposal.interrupt", return_value={"action": "approve"}),
        ):
            await draft_proposal(base_state)

        prompt_text = mock.ainvoke.call_args[0][0][1].content
        assert "Snowflake" in prompt_text
        assert "80" in prompt_text

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        revised = "# Revised Proposal\n\nUpdated content..."
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=self.PROPOSAL_TEXT),
                         AIMessage(content=revised)]
        )

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock),
            patch("src.graph.proposal.draft_proposal.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Emphasize cost savings more"},
                      {"action": "approve"},
                  ]),
        ):
            result = await draft_proposal(base_state)

        assert mock.ainvoke.call_count == 2
        proposal_doc = next(d for d in result["generated_docs"] if d["type"] == "proposal_narrative")
        assert "Revised" in proposal_doc["content"]

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.PROPOSAL_TEXT)

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock),
            patch("src.graph.proposal.draft_proposal.interrupt", return_value={"action": "reject"}),
        ):
            result = await draft_proposal(base_state)

        assert result.get("error") is not None
        assert result["last_node"] == "draft_proposal"

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.PROPOSAL_TEXT)

        with (
            patch("src.graph.proposal.draft_proposal.get_llm", return_value=mock) as mock_get,
            patch("src.graph.proposal.draft_proposal.interrupt", return_value={"action": "approve"}),
        ):
            await draft_proposal(base_state)

        mock_get.assert_called_once_with("strong")


# --- add_reference_architecture tests ---

class TestAddReferenceArchitecture:
    ARCH_SECTION = (
        "# Reference Architecture\n\n"
        "## Current State Architecture\n"
        "```mermaid\ngraph LR\n  PG[PostgreSQL] --> S3\n  S3 --> SF[Snowflake]\n```\n\n"
        "## Target State Architecture\n"
        "```mermaid\ngraph LR\n  PG[PostgreSQL] --> S3\n  S3 --> Tower[Tower/Iceberg]\n```\n\n"
        "## Migration Architecture\n"
        "Both Snowflake and Tower run in parallel during transition.\n\n"
        "## Component Mapping\n"
        "| Current | Target | Action |\n|---|---|---|\n| Snowflake | Tower | Replace |\n"
    )

    @pytest.mark.asyncio
    async def test_produces_architecture_section(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_SECTION)

        with (
            patch("src.graph.proposal.add_reference_architecture.get_llm", return_value=mock),
            patch("src.graph.proposal.add_reference_architecture.interrupt", return_value={"action": "approve"}),
        ):
            result = await add_reference_architecture(base_state)

        assert result["last_node"] == "add_reference_architecture"
        arch_doc = next(d for d in result["generated_docs"] if d["type"] == "reference_architecture")
        assert "mermaid" in arch_doc["content"]

    @pytest.mark.asyncio
    async def test_reads_poc_architecture(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_SECTION)

        with (
            patch("src.graph.proposal.add_reference_architecture.get_llm", return_value=mock),
            patch("src.graph.proposal.add_reference_architecture.interrupt", return_value={"action": "approve"}),
        ):
            await add_reference_architecture(base_state)

        prompt_text = mock.ainvoke.call_args[0][0][1].content
        assert "component_mapping" in prompt_text or "Tower" in prompt_text

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        revised = "# Revised Architecture\n\nUpdated diagrams..."
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=self.ARCH_SECTION),
                         AIMessage(content=revised)]
        )

        with (
            patch("src.graph.proposal.add_reference_architecture.get_llm", return_value=mock),
            patch("src.graph.proposal.add_reference_architecture.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Add Spark to the diagram"},
                      {"action": "approve"},
                  ]),
        ):
            result = await add_reference_architecture(base_state)

        assert mock.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_SECTION)

        with (
            patch("src.graph.proposal.add_reference_architecture.get_llm", return_value=mock),
            patch("src.graph.proposal.add_reference_architecture.interrupt", return_value={"action": "reject"}),
        ):
            result = await add_reference_architecture(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.ARCH_SECTION)

        with (
            patch("src.graph.proposal.add_reference_architecture.get_llm", return_value=mock) as mock_get,
            patch("src.graph.proposal.add_reference_architecture.interrupt", return_value={"action": "approve"}),
        ):
            await add_reference_architecture(base_state)

        mock_get.assert_called_once_with("strong")


# --- add_deployment_plan tests ---

class TestAddDeploymentPlan:
    DEPLOYMENT_TEXT = (
        "# Deployment Plan — Acme Corp\n\n"
        "## Phase 1: PoC Validation (Complete)\n"
        "Two-week PoC migrating orders pipeline demonstrated...\n\n"
        "## Phase 2: Production Pilot (4-6 weeks)\n"
        "Migrate orders pipeline to production Tower environment...\n\n"
        "## Phase 3: Broader Rollout (2-4 months)\n"
        "Migrate remaining analytics workloads...\n\n"
        "## Phase 4: Optimization & Expansion\n"
        "Performance tuning and advanced features...\n\n"
        "## Risk Mitigation\n"
        "- dbt adapter compatibility: pin to stable version\n\n"
        "## Investment Summary\n"
        "Total timeline: 4-6 months from PoC to full production."
    )

    @pytest.mark.asyncio
    async def test_produces_deployment_plan(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.DEPLOYMENT_TEXT)

        with (
            patch("src.graph.proposal.add_deployment_plan.get_llm", return_value=mock),
            patch("src.graph.proposal.add_deployment_plan.interrupt", return_value={"action": "approve"}),
        ):
            result = await add_deployment_plan(base_state)

        assert result["last_node"] == "add_deployment_plan"
        plan_doc = next(d for d in result["generated_docs"] if d["type"] == "deployment_plan")
        assert "Phase" in plan_doc["content"]

    @pytest.mark.asyncio
    async def test_reads_poc_plan_and_architecture(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.DEPLOYMENT_TEXT)

        with (
            patch("src.graph.proposal.add_deployment_plan.get_llm", return_value=mock),
            patch("src.graph.proposal.add_deployment_plan.interrupt", return_value={"action": "approve"}),
        ):
            await add_deployment_plan(base_state)

        prompt_text = mock.ainvoke.call_args[0][0][1].content
        assert "Tower" in prompt_text

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        revised = "# Revised Deployment Plan\n\nUpdated phases..."
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=self.DEPLOYMENT_TEXT),
                         AIMessage(content=revised)]
        )

        with (
            patch("src.graph.proposal.add_deployment_plan.get_llm", return_value=mock),
            patch("src.graph.proposal.add_deployment_plan.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Extend Phase 2 to 8 weeks"},
                      {"action": "approve"},
                  ]),
        ):
            result = await add_deployment_plan(base_state)

        assert mock.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.DEPLOYMENT_TEXT)

        with (
            patch("src.graph.proposal.add_deployment_plan.get_llm", return_value=mock),
            patch("src.graph.proposal.add_deployment_plan.interrupt", return_value={"action": "reject"}),
        ):
            result = await add_deployment_plan(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        mock = mock_llm_response(self.DEPLOYMENT_TEXT)

        with (
            patch("src.graph.proposal.add_deployment_plan.get_llm", return_value=mock) as mock_get,
            patch("src.graph.proposal.add_deployment_plan.interrupt", return_value={"action": "approve"}),
        ):
            await add_deployment_plan(base_state)

        mock_get.assert_called_once_with("strong")


# --- compile_document tests ---

class TestCompileDocument:
    @pytest.mark.asyncio
    async def test_assembles_proposal_sections(self, base_state):
        base_state["generated_docs"].extend([
            {
                "type": "proposal_narrative",
                "title": "Proposal — Acme Corp",
                "content": "# Executive Summary\nAcme Corp proposal...",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
            {
                "type": "reference_architecture",
                "title": "Reference Architecture — Acme Corp",
                "content": "# Reference Architecture\n```mermaid\ngraph LR\n```",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
            {
                "type": "deployment_plan",
                "title": "Deployment Plan — Acme Corp",
                "content": "# Deployment Plan\nPhase 1...",
                "gdrive_url": None,
                "created_at": "2026-03-19T00:00:00Z",
            },
        ])

        with (
            patch("src.graph.proposal.compile_document.interrupt", return_value={"action": "approve"}),
            patch("src.graph.proposal.compile_document.get_gdrive_client", return_value=None),
        ):
            result = await compile_document(base_state)

        assert result["last_node"] == "compile_document"
        compiled = next(d for d in result["generated_docs"] if d["type"] == "compiled_proposal")
        assert "Executive Summary" in compiled["content"]
        assert "Reference Architecture" in compiled["content"]
        assert "Deployment Plan" in compiled["content"]

    @pytest.mark.asyncio
    async def test_uploads_to_gdrive(self, base_state):
        base_state["generated_docs"].extend([
            {"type": "proposal_narrative", "title": "t", "content": "Proposal text", "gdrive_url": None, "created_at": ""},
            {"type": "reference_architecture", "title": "t", "content": "Arch text", "gdrive_url": None, "created_at": ""},
            {"type": "deployment_plan", "title": "t", "content": "Plan text", "gdrive_url": None, "created_at": ""},
        ])
        mock_gdrive = MagicMock()
        mock_gdrive.create_doc.return_value = "https://docs.google.com/document/d/xyz/edit"

        with (
            patch("src.graph.proposal.compile_document.interrupt", return_value={"action": "approve"}),
            patch("src.graph.proposal.compile_document.get_gdrive_client", return_value=mock_gdrive),
        ):
            result = await compile_document(base_state)

        mock_gdrive.create_doc.assert_called_once()
        compiled = next(d for d in result["generated_docs"] if d["type"] == "compiled_proposal")
        assert compiled["gdrive_url"] == "https://docs.google.com/document/d/xyz/edit"

    @pytest.mark.asyncio
    async def test_graceful_without_gdrive(self, base_state):
        base_state["generated_docs"].extend([
            {"type": "proposal_narrative", "title": "t", "content": "Proposal text", "gdrive_url": None, "created_at": ""},
            {"type": "reference_architecture", "title": "t", "content": "Arch text", "gdrive_url": None, "created_at": ""},
            {"type": "deployment_plan", "title": "t", "content": "Plan text", "gdrive_url": None, "created_at": ""},
        ])

        with (
            patch("src.graph.proposal.compile_document.interrupt", return_value={"action": "approve"}),
            patch("src.graph.proposal.compile_document.get_gdrive_client", return_value=None),
        ):
            result = await compile_document(base_state)

        compiled = next(d for d in result["generated_docs"] if d["type"] == "compiled_proposal")
        assert compiled["gdrive_url"] is None

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state):
        base_state["generated_docs"].extend([
            {"type": "proposal_narrative", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
            {"type": "reference_architecture", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
            {"type": "deployment_plan", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
        ])

        with (
            patch("src.graph.proposal.compile_document.interrupt", return_value={"action": "reject"}),
            patch("src.graph.proposal.compile_document.get_gdrive_client", return_value=None),
        ):
            result = await compile_document(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_no_llm_call(self, base_state):
        base_state["generated_docs"].extend([
            {"type": "proposal_narrative", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
            {"type": "reference_architecture", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
            {"type": "deployment_plan", "title": "t", "content": "text", "gdrive_url": None, "created_at": ""},
        ])

        with (
            patch("src.graph.proposal.compile_document.interrupt", return_value={"action": "approve"}),
            patch("src.graph.proposal.compile_document.get_gdrive_client", return_value=None),
        ):
            result = await compile_document(base_state)

        assert result["last_node"] == "compile_document"
