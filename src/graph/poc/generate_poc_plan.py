import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.poc import GENERATE_POC_PLAN_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_architecture(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "poc_architecture":
            return json.dumps(s["content"], indent=2)
    return "No architecture document available yet."


def _get_poc_requirements(state: CustomerState) -> str:
    messages = state.get("messages", [])
    return messages[-1].content if messages else "No PoC requirements provided."


async def generate_poc_plan(state: CustomerState) -> dict:
    llm = get_llm("strong")

    prompt = GENERATE_POC_PLAN_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        architecture_json=_get_architecture(state),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        poc_requirements=_get_poc_requirements(state),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        tech_env_json=json.dumps(state.get("tech_env", {}), indent=2),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        poc_plan = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            poc_plan = json.loads(content[start:end])
        else:
            return {"last_node": "generate_poc_plan", "error": "Failed to parse PoC plan"}

    decision = interrupt({
        "type": "review_poc_plan",
        "poc_plan": poc_plan,
        "customer": state.get("customer_name", ""),
        "instructions": "Review PoC plan. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, poc_plan)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the PoC plan with these changes:\n{revision_instructions}"),
        ])
        try:
            revised_plan = json.loads(revised.content)
        except json.JSONDecodeError:
            revised_plan = {"poc_summary": revised.content}

        decision2 = interrupt({
            "type": "review_poc_plan",
            "poc_plan": revised_plan,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised PoC plan. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_plan)

    return {"last_node": "generate_poc_plan", "error": "PoC plan rejected by FDE"}


def _build_approve_result(state: CustomerState, poc_plan: dict) -> dict:
    summary = poc_plan.get("poc_summary", json.dumps(poc_plan, indent=2))
    doc_record = {
        "type": "poc_plan",
        "title": f"PoC Plan — {state.get('customer_name', 'Unknown')}",
        "content": summary,
        "gdrive_url": None,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "generate_poc_plan",
    }
