import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.poc import DESIGN_ARCHITECTURE_PROMPT
from src.llm.prompts.system_tower import (
    TOWER_SYSTEM_CONTEXT,
    load_iceberg_patterns,
    load_tower_knowledge,
)

logger = logging.getLogger(__name__)


def _get_stack_analysis(state: CustomerState) -> str:
    for s in state.get("meeting_summaries", []):
        if s.get("type") == "stack_analysis":
            return json.dumps(s["content"], indent=2)
    return "No stack analysis available yet."


async def design_architecture(state: CustomerState) -> dict:
    llm = get_llm("strong")

    prompt = DESIGN_ARCHITECTURE_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        tower_knowledge=load_tower_knowledge(),
        iceberg_patterns=load_iceberg_patterns(),
        tech_env_json=json.dumps(state.get("tech_env", {}), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        stack_analysis=_get_stack_analysis(state),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        architecture = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            architecture = json.loads(content[start:end])
        else:
            return {"last_node": "design_architecture", "error": "Failed to parse architecture"}

    decision = interrupt({
        "type": "review_poc_architecture",
        "architecture": architecture,
        "customer": state.get("customer_name", ""),
        "instructions": "Review target architecture. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, architecture)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the architecture with these changes:\n{revision_instructions}"),
        ])
        try:
            revised_arch = json.loads(revised.content)
        except json.JSONDecodeError:
            revised_arch = {"architecture_summary": revised.content}

        decision2 = interrupt({
            "type": "review_poc_architecture",
            "architecture": revised_arch,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised architecture. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_arch)

    return {"last_node": "design_architecture", "error": "Architecture rejected by FDE"}


def _build_approve_result(state: CustomerState, architecture: dict) -> dict:
    summary = architecture.get("architecture_summary", json.dumps(architecture, indent=2))
    doc_record = {
        "type": "poc_architecture",
        "title": f"PoC Architecture — {state.get('customer_name', 'Unknown')}",
        "content": summary,
        "gdrive_url": None,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "meeting_summaries": state.get("meeting_summaries", []) + [
            {"type": "poc_architecture", "content": architecture}
        ],
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "design_architecture",
    }
