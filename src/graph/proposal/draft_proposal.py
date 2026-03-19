import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.proposal import DRAFT_PROPOSAL_PROMPT
from src.llm.prompts.system_tower import (
    TOWER_SYSTEM_CONTEXT,
    load_tower_knowledge,
)

logger = logging.getLogger(__name__)


def _get_doc_content(state: CustomerState, doc_type: str) -> str:
    for doc in reversed(state.get("generated_docs", [])):
        if doc.get("type") == doc_type:
            return doc.get("content", "")
    return "Not available."


async def draft_proposal(state: CustomerState) -> dict:
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    prompt = DRAFT_PROPOSAL_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        tower_knowledge=load_tower_knowledge(),
        tech_env_json=json.dumps(tech_env, indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        metrics=state.get("metrics", "Not specified"),
        economic_buyer=state.get("economic_buyer", "Not identified"),
        decision_criteria_json=json.dumps(state.get("decision_criteria", []), indent=2),
        decision_process=state.get("decision_process", "Not specified"),
        pain_points_json=json.dumps(state.get("identified_pain", []), indent=2),
        champion=state.get("champion", "Not identified"),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        discovery_summary=_get_doc_content(state, "discovery_summary"),
        competitive_summary=_get_doc_content(state, "competitive_positioning"),
        data_volume_tb=tech_env.get("data_volume_tb", "unknown"),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    proposal_text = response.content

    decision = interrupt({
        "type": "review_proposal_narrative",
        "document": proposal_text,
        "customer": state.get("customer_name", ""),
        "instructions": "Review proposal narrative. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, proposal_text)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the proposal with these changes:\n{revision_instructions}"),
        ])
        revised_text = revised.content

        decision2 = interrupt({
            "type": "review_proposal_narrative",
            "document": revised_text,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised proposal. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_text)

    return {"last_node": "draft_proposal", "error": "Proposal rejected by FDE"}


def _build_approve_result(state: CustomerState, proposal_text: str) -> dict:
    doc_record = {
        "type": "proposal_narrative",
        "title": f"Technical Proposal — {state.get('customer_name', 'Unknown')}",
        "content": proposal_text,
        "gdrive_url": None,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "draft_proposal",
    }
