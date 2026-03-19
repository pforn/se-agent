import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.integrations.gdrive import get_gdrive_client
from src.llm.models import get_llm
from src.llm.prompts.poc import CREATE_DEMO_SCRIPT_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_architecture(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "poc_architecture":
            return json.dumps(s["content"], indent=2)
    return "No architecture document available."


def _get_poc_plan(state: CustomerState) -> str:
    for doc in reversed(state.get("generated_docs", [])):
        if doc.get("type") == "poc_plan":
            return doc.get("content", "")
    return "No PoC plan available."


def _upload_to_gdrive(title: str, content: str) -> str | None:
    client = get_gdrive_client()
    if client is None:
        return None
    try:
        return client.create_doc(title, content)
    except Exception:
        logger.warning("Failed to upload demo script to Google Drive", exc_info=True)
        return None


async def create_demo_script(state: CustomerState) -> dict:
    llm = get_llm("strong")

    prompt = CREATE_DEMO_SCRIPT_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        architecture_json=_get_architecture(state),
        poc_plan_json=_get_poc_plan(state),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        tech_env_json=json.dumps(state.get("tech_env", {}), indent=2),
        current_warehouse=state.get("tech_env", {}).get("current_warehouse", "current stack"),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    demo_script = response.content

    decision = interrupt({
        "type": "review_demo_script",
        "document": demo_script,
        "customer": state.get("customer_name", ""),
        "instructions": "Review demo script. Approve to save/upload, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, demo_script)
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Revise the demo script with these changes:\n{revision_instructions}"),
        ])
        revised_script = revised.content

        decision2 = interrupt({
            "type": "review_demo_script",
            "document": revised_script,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised demo script. Approve or reject.",
        })
        if decision2.get("action") == "approve":
            return _build_approve_result(state, revised_script)

    return {"last_node": "create_demo_script", "error": "Demo script rejected by FDE"}


def _build_approve_result(state: CustomerState, demo_script: str) -> dict:
    title = f"Demo Script — {state.get('customer_name', 'Unknown')}"
    gdrive_url = _upload_to_gdrive(title, demo_script)

    doc_record = {
        "type": "demo_script",
        "title": title,
        "content": demo_script,
        "gdrive_url": gdrive_url,
        "created_at": state.get("updated_at", ""),
    }
    return {
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "create_demo_script",
    }
