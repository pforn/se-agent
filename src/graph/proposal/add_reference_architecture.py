import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.proposal import ADD_REFERENCE_ARCHITECTURE_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_architecture(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "poc_architecture":
            return json.dumps(s["content"], indent=2)
    return "No architecture document available."


def _get_proposal_narrative(state: CustomerState) -> str:
    for doc in reversed(state.get("generated_docs", [])):
        if doc.get("type") == "proposal_narrative":
            return doc.get("content", "")
    return "No proposal narrative available yet."


async def add_reference_architecture(state: CustomerState) -> dict:
    llm = get_llm("strong")

    prompt = ADD_REFERENCE_ARCHITECTURE_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        architecture_json=_get_architecture(state),
        tech_env_json=json.dumps(state.get("tech_env", {}), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        proposal_narrative=_get_proposal_narrative(state),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    arch_section = response.content

    decision = interrupt({
        "type": "review_reference_architecture",
        "document": arch_section,
        "customer": state.get("customer_name", ""),
        "instructions": "Review reference architecture section. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, arch_section)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the architecture section with these changes:\n{revision_instructions}"),
        ])
        revised_section = revised.content

        decision2 = interrupt({
            "type": "review_reference_architecture",
            "document": revised_section,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised architecture section. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_section)

    return {"last_node": "add_reference_architecture", "error": "Reference architecture rejected by FDE"}


def _build_approve_result(state: CustomerState, arch_section: str) -> dict:
    doc_record = {
        "type": "reference_architecture",
        "title": f"Reference Architecture — {state.get('customer_name', 'Unknown')}",
        "content": arch_section,
        "gdrive_url": None,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "add_reference_architecture",
    }
