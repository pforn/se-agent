import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.followup import EXTRACT_ACTION_ITEMS_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT


def _get_latest_summary(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "meeting_summary":
            content = s.get("content", {})
            return content.get("raw_summary", json.dumps(content, indent=2))
    return ""


async def extract_action_items(state: CustomerState) -> dict:
    llm = get_llm("strong")

    meeting_summary = _get_latest_summary(state)
    existing_items = state.get("action_items", [])

    prompt = EXTRACT_ACTION_ITEMS_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        meeting_summary=meeting_summary,
        existing_action_items=json.dumps(existing_items, indent=2) if existing_items else "None",
        created_at=state.get("updated_at", ""),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        action_items = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            action_items = json.loads(content[start:end])
        else:
            action_items = []

    if not isinstance(action_items, list):
        action_items = [action_items]

    decision = interrupt({
        "type": "review_action_items",
        "action_items": action_items,
        "customer": state.get("customer_name", ""),
        "instructions": "Review extracted action items. Approve, edit assignments, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return {
            "action_items": existing_items + action_items,
            "last_node": "extract_action_items",
        }
    elif action == "edit":
        edited = decision.get("action_items", action_items)
        return {
            "action_items": existing_items + edited,
            "last_node": "extract_action_items",
        }

    return {"last_node": "extract_action_items", "error": "Action items rejected by FDE"}
