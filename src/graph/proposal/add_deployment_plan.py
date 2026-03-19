import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.proposal import ADD_DEPLOYMENT_PLAN_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_architecture(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "poc_architecture":
            return json.dumps(s["content"], indent=2)
    return "No architecture document available."


def _get_doc_content(state: CustomerState, doc_type: str) -> str:
    for doc in reversed(state.get("generated_docs", [])):
        if doc.get("type") == doc_type:
            return doc.get("content", "")
    return "Not available."


async def add_deployment_plan(state: CustomerState) -> dict:
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    prompt = ADD_DEPLOYMENT_PLAN_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        architecture_json=_get_architecture(state),
        poc_plan=_get_doc_content(state, "poc_plan"),
        proposal_narrative=_get_doc_content(state, "proposal_narrative"),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        tech_env_json=json.dumps(tech_env, indent=2),
        data_volume_tb=tech_env.get("data_volume_tb", "unknown"),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    plan_text = response.content

    decision = interrupt({
        "type": "review_deployment_plan",
        "document": plan_text,
        "customer": state.get("customer_name", ""),
        "instructions": "Review deployment plan. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, plan_text)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the deployment plan with these changes:\n{revision_instructions}"),
        ])
        revised_text = revised.content

        decision2 = interrupt({
            "type": "review_deployment_plan",
            "document": revised_text,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised deployment plan. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_text)

    return {"last_node": "add_deployment_plan", "error": "Deployment plan rejected by FDE"}


def _build_approve_result(state: CustomerState, plan_text: str) -> dict:
    doc_record = {
        "type": "deployment_plan",
        "title": f"Deployment Plan — {state.get('customer_name', 'Unknown')}",
        "content": plan_text,
        "gdrive_url": None,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "add_deployment_plan",
    }
