import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.followup.summarize_meeting import summarize_meeting
from src.graph.followup.extract_action_items import extract_action_items
from src.graph.followup.extract_product_feedback import extract_product_feedback
from src.graph.followup.update_health_score import update_health_score
from src.graph.followup.draft_followup_email import draft_followup_email


MEETING_NOTES = (
    "Attendees: Jordan Chen (Head of Data Eng), Sarah Kim (VP Eng), me\n\n"
    "Key discussion points:\n"
    "1. Snowflake contract renews in Q3\n"
    "2. Jordan is the technical champion\n"
    "3. Sarah cares about TCO\n"
    "4. SOC2 Type II compliance needed\n"
    "5. ML feature store use case\n"
    "6. Databricks pitched Delta UniForm\n"
    "7. Next steps: reference architecture, dbt project share, eng input"
)


@pytest.fixture
def base_state():
    return {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "followup",
        "tech_env": {
            "current_warehouse": "Snowflake Enterprise",
            "cloud_provider": "aws",
            "data_volume_tb": 80.0,
        },
        "use_cases": [
            {
                "name": "Analytics Migration",
                "description": "Migrate from Snowflake to Tower",
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
        "decision_criteria": ["TCO", "migration effort"],
        "decision_process": "PoC then executive review",
        "identified_pain": ["Snowflake costs 3x YoY"],
        "champion": "Jordan Chen",
        "health_score": 70,
        "messages": [HumanMessage(content=MEETING_NOTES)],
        "action_items": [],
        "product_feedback": [],
        "competitive_intel": [],
        "meeting_summaries": [],
        "generated_docs": [],
        "pending_approval": None,
        "last_node": None,
        "error": None,
        "created_at": "2026-03-18T00:00:00Z",
        "updated_at": "2026-03-18T00:00:00Z",
    }


@pytest.fixture
def mock_llm_response():
    def _make(content: str | dict):
        if isinstance(content, dict) or isinstance(content, list):
            content = json.dumps(content)
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(content=content))
        return mock
    return _make


# --- summarize_meeting tests ---

class TestSummarizeMeeting:
    @pytest.mark.asyncio
    async def test_produces_meeting_summary(self, base_state, mock_llm_response):
        llm_output = {
            "attendees": [
                {"name": "Jordan Chen", "role": "Head of Data Eng"},
                {"name": "Sarah Kim", "role": "VP Eng"},
            ],
            "date": "2026-03-18",
            "key_topics": ["Snowflake renewal", "TCO", "SOC2"],
            "decisions": ["Proceed with PoC evaluation"],
            "next_steps": ["Send reference architecture"],
            "sentiment_summary": "Positive overall, Sarah cautious on cost",
            "raw_summary": "Met with Acme Corp to discuss migration.",
        }
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.summarize_meeting.get_llm", return_value=mock),
            patch("src.graph.followup.summarize_meeting.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.summarize_meeting.index_meeting_notes"),
        ):
            result = await summarize_meeting(base_state)

        assert result["last_node"] == "summarize_meeting"
        assert len(result["meeting_summaries"]) == 1
        assert result["meeting_summaries"][0]["type"] == "meeting_summary"

    @pytest.mark.asyncio
    async def test_indexes_on_approve(self, base_state, mock_llm_response):
        llm_output = {
            "attendees": [], "date": None, "key_topics": [],
            "decisions": [], "next_steps": [],
            "sentiment_summary": "Good", "raw_summary": "Summary text.",
        }
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.summarize_meeting.get_llm", return_value=mock),
            patch("src.graph.followup.summarize_meeting.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.summarize_meeting.index_meeting_notes") as mock_index,
        ):
            await summarize_meeting(base_state)

        mock_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        llm_output = {
            "attendees": [], "date": None, "key_topics": [],
            "decisions": [], "next_steps": [],
            "sentiment_summary": "", "raw_summary": "",
        }
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.summarize_meeting.get_llm", return_value=mock),
            patch("src.graph.followup.summarize_meeting.interrupt", return_value={"action": "reject"}),
        ):
            result = await summarize_meeting(base_state)

        assert result.get("error") is not None
        assert result["last_node"] == "summarize_meeting"

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        llm_output = {
            "attendees": [], "date": None, "key_topics": [],
            "decisions": [], "next_steps": [],
            "sentiment_summary": "", "raw_summary": "",
        }
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.summarize_meeting.get_llm", return_value=mock) as mock_get,
            patch("src.graph.followup.summarize_meeting.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.summarize_meeting.index_meeting_notes"),
        ):
            await summarize_meeting(base_state)

        mock_get.assert_called_once_with("strong")


# --- extract_action_items tests ---

class TestExtractActionItems:
    @pytest.mark.asyncio
    async def test_extracts_action_items(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Discussed next steps."}}
        ]
        llm_output = [
            {
                "description": "Send reference architecture to Jordan",
                "owner": "fde",
                "due_date": "2026-03-20",
                "status": "open",
                "created_at": "2026-03-18T00:00:00Z",
            },
            {
                "description": "Share dbt project structure",
                "owner": "customer",
                "due_date": None,
                "status": "open",
                "created_at": "2026-03-18T00:00:00Z",
            },
        ]
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.extract_action_items.get_llm", return_value=mock),
            patch("src.graph.followup.extract_action_items.interrupt", return_value={"action": "approve"}),
        ):
            result = await extract_action_items(base_state)

        assert result["last_node"] == "extract_action_items"
        assert len(result["action_items"]) == 2
        assert result["action_items"][0]["owner"] == "fde"
        assert result["action_items"][1]["owner"] == "customer"

    @pytest.mark.asyncio
    async def test_edit_replaces_action_items(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        llm_output = [
            {"description": "Original", "owner": "fde", "due_date": None,
             "status": "open", "created_at": "2026-03-18T00:00:00Z"},
        ]
        edited = [
            {"description": "Edited item", "owner": "customer", "due_date": "2026-03-25",
             "status": "open", "created_at": "2026-03-18T00:00:00Z"},
        ]
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.extract_action_items.get_llm", return_value=mock),
            patch("src.graph.followup.extract_action_items.interrupt",
                  return_value={"action": "edit", "action_items": edited}),
        ):
            result = await extract_action_items(base_state)

        assert result["action_items"][0]["description"] == "Edited item"

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        mock = mock_llm_response([])

        with (
            patch("src.graph.followup.extract_action_items.get_llm", return_value=mock) as mock_get,
            patch("src.graph.followup.extract_action_items.interrupt", return_value={"action": "approve"}),
        ):
            await extract_action_items(base_state)

        mock_get.assert_called_once_with("strong")


# --- extract_product_feedback tests ---

class TestExtractProductFeedback:
    @pytest.mark.asyncio
    async def test_extracts_feedback(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "SOC2 needed. dbt 1.8 concern."}}
        ]
        llm_output = [
            {
                "feature_area": "security",
                "description": "SOC2 Type II certification needed",
                "customer": "Acme Corp",
                "severity": "important",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
            {
                "feature_area": "dbt integration",
                "description": "dbt-core 1.8 compatibility",
                "customer": "Acme Corp",
                "severity": "blocker",
                "created_at": "2026-03-18T00:00:00Z",
                "ticket_url": None,
            },
        ]
        mock = mock_llm_response(llm_output)

        with (
            patch("src.graph.followup.extract_product_feedback.get_llm", return_value=mock),
            patch("src.graph.followup.extract_product_feedback.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.extract_product_feedback.index_product_feedback"),
        ):
            result = await extract_product_feedback(base_state)

        assert result["last_node"] == "extract_product_feedback"
        assert len(result["product_feedback"]) == 2
        assert result["product_feedback"][0]["severity"] == "important"

    @pytest.mark.asyncio
    async def test_indexes_on_approve(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes"}}
        ]
        mock = mock_llm_response([])

        with (
            patch("src.graph.followup.extract_product_feedback.get_llm", return_value=mock),
            patch("src.graph.followup.extract_product_feedback.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.extract_product_feedback.index_product_feedback") as mock_index,
        ):
            await extract_product_feedback(base_state)

        mock_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_fast_llm(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes"}}
        ]
        mock = mock_llm_response([])

        with (
            patch("src.graph.followup.extract_product_feedback.get_llm", return_value=mock) as mock_get,
            patch("src.graph.followup.extract_product_feedback.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.extract_product_feedback.index_product_feedback"),
        ):
            await extract_product_feedback(base_state)

        mock_get.assert_called_once_with("fast")


# --- update_health_score tests ---

class TestUpdateHealthScore:
    @pytest.mark.asyncio
    async def test_updates_health_score(self, base_state, mock_llm_response):
        llm_output = {
            "health_score": 85,
            "score_breakdown": {
                "champion": 20, "economic_buyer": 15, "pain_points": 15,
                "timeline": 15, "tower_fit": 15, "compatibility": 10,
                "stakeholders": 10,
            },
            "change_reason": "Strong champion identified, clear timeline",
        }
        mock = mock_llm_response(llm_output)

        with patch("src.graph.followup.update_health_score.get_llm", return_value=mock):
            result = await update_health_score(base_state)

        assert result["last_node"] == "update_health_score"
        assert result["health_score"] == 85

    @pytest.mark.asyncio
    async def test_uses_fast_llm(self, base_state, mock_llm_response):
        llm_output = {"health_score": 70, "score_breakdown": {}, "change_reason": "No change"}
        mock = mock_llm_response(llm_output)

        with patch("src.graph.followup.update_health_score.get_llm", return_value=mock) as mock_get:
            await update_health_score(base_state)

        mock_get.assert_called_once_with("fast")

    @pytest.mark.asyncio
    async def test_handles_parse_failure(self, base_state, mock_llm_response):
        mock = mock_llm_response("Not valid JSON at all")

        with patch("src.graph.followup.update_health_score.get_llm", return_value=mock):
            result = await update_health_score(base_state)

        assert result["last_node"] == "update_health_score"
        assert "error" in result


# --- draft_followup_email tests ---

class TestDraftFollowupEmail:
    @pytest.mark.asyncio
    async def test_drafts_email_on_approve(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Good meeting."}}
        ]
        base_state["action_items"] = [
            {"description": "Send arch doc", "owner": "fde", "due_date": None,
             "status": "open", "created_at": "2026-03-18T00:00:00Z"},
        ]
        email_text = "Subject: Follow-up: Acme Corp meeting\n\nHi Jordan and Sarah,\n\nThank you for the call..."
        mock = mock_llm_response(email_text)

        with (
            patch("src.graph.followup.draft_followup_email.get_llm", return_value=mock),
            patch("src.graph.followup.draft_followup_email.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.draft_followup_email.get_gdrive_client", return_value=None),
        ):
            result = await draft_followup_email(base_state)

        assert result["last_node"] == "draft_followup_email"
        assert len(result["generated_docs"]) == 1
        assert result["generated_docs"][0]["type"] == "followup_email"
        assert result["generated_docs"][0]["gdrive_url"] is None

    @pytest.mark.asyncio
    async def test_uploads_to_gdrive_when_available(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        email_text = "Subject: Follow-up\n\nThank you..."
        mock = mock_llm_response(email_text)

        mock_gdrive = MagicMock()
        mock_gdrive.create_doc.return_value = "https://docs.google.com/document/d/xyz/edit"

        with (
            patch("src.graph.followup.draft_followup_email.get_llm", return_value=mock),
            patch("src.graph.followup.draft_followup_email.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.draft_followup_email.get_gdrive_client", return_value=mock_gdrive),
        ):
            result = await draft_followup_email(base_state)

        mock_gdrive.create_doc.assert_called_once()
        assert result["generated_docs"][0]["gdrive_url"] == "https://docs.google.com/document/d/xyz/edit"

    @pytest.mark.asyncio
    async def test_edit_flow(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        original = "Subject: Original\n\nFirst draft..."
        revised = "Subject: Revised\n\nRevised draft..."
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(
            side_effect=[AIMessage(content=original), AIMessage(content=revised)]
        )

        with (
            patch("src.graph.followup.draft_followup_email.get_llm", return_value=mock),
            patch("src.graph.followup.draft_followup_email.interrupt",
                  side_effect=[
                      {"action": "edit", "edits": "Make it shorter"},
                      {"action": "approve"},
                  ]),
            patch("src.graph.followup.draft_followup_email.get_gdrive_client", return_value=None),
        ):
            result = await draft_followup_email(base_state)

        assert result["generated_docs"][0]["content"] == revised
        assert mock.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_reject_sets_error(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        mock = mock_llm_response("Subject: Test\n\nEmail text")

        with (
            patch("src.graph.followup.draft_followup_email.get_llm", return_value=mock),
            patch("src.graph.followup.draft_followup_email.interrupt", return_value={"action": "reject"}),
        ):
            result = await draft_followup_email(base_state)

        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_uses_strong_llm(self, base_state, mock_llm_response):
        base_state["meeting_summaries"] = [
            {"type": "meeting_summary", "content": {"raw_summary": "Notes."}}
        ]
        mock = mock_llm_response("Subject: Test\n\nEmail")

        with (
            patch("src.graph.followup.draft_followup_email.get_llm", return_value=mock) as mock_get,
            patch("src.graph.followup.draft_followup_email.interrupt", return_value={"action": "approve"}),
            patch("src.graph.followup.draft_followup_email.get_gdrive_client", return_value=None),
        ):
            await draft_followup_email(base_state)

        mock_get.assert_called_once_with("strong")
