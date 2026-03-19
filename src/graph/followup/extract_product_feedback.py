import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.kb.indexer import index_product_feedback
from src.llm.models import get_llm
from src.llm.prompts.followup import EXTRACT_PRODUCT_FEEDBACK_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_latest_summary(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "meeting_summary":
            content = s.get("content", {})
            return content.get("raw_summary", json.dumps(content, indent=2))
    return ""


async def extract_product_feedback(state: CustomerState) -> dict:
    llm = get_llm("fast")

    meeting_summary = _get_latest_summary(state)
    action_items = state.get("action_items", [])

    prompt = EXTRACT_PRODUCT_FEEDBACK_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        meeting_summary=meeting_summary,
        action_items_json=json.dumps(action_items, indent=2) if action_items else "None",
        created_at=state.get("updated_at", ""),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        feedback = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            feedback = json.loads(content[start:end])
        else:
            feedback = []

    if not isinstance(feedback, list):
        feedback = [feedback]

    decision = interrupt({
        "type": "review_product_feedback",
        "product_feedback": feedback,
        "customer": state.get("customer_name", ""),
        "instructions": "Review product feedback and severity ratings. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        merged_state = {**state, "product_feedback": feedback}
        try:
            index_product_feedback(merged_state)
        except Exception:
            logger.warning("Failed to index product feedback", exc_info=True)

        return {"product_feedback": feedback, "last_node": "extract_product_feedback"}
    elif action == "edit":
        edited = decision.get("product_feedback", feedback)
        return {"product_feedback": edited, "last_node": "extract_product_feedback"}

    return {"last_node": "extract_product_feedback", "error": "Product feedback rejected by FDE"}
