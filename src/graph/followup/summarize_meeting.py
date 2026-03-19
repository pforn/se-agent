import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.kb.indexer import index_meeting_notes
from src.llm.models import get_llm
from src.llm.prompts.followup import SUMMARIZE_MEETING_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


async def summarize_meeting(state: CustomerState) -> dict:
    llm = get_llm("strong")

    messages = state.get("messages", [])
    meeting_notes = messages[-1].content if messages else ""

    existing_context = ""
    if state.get("tech_env"):
        existing_context += f"Technical environment: {json.dumps(state['tech_env'], indent=2)}\n"
    if state.get("stakeholders"):
        existing_context += f"Known stakeholders: {json.dumps(state['stakeholders'], indent=2)}\n"

    prompt = SUMMARIZE_MEETING_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        meeting_notes=meeting_notes,
        existing_context=existing_context or "None",
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        summary = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            summary = json.loads(content[start:end])
        else:
            return {"last_node": "summarize_meeting", "error": "Failed to parse meeting summary"}

    decision = interrupt({
        "type": "review_meeting_summary",
        "summary": summary,
        "customer": state.get("customer_name", ""),
        "instructions": "Review meeting summary. Approve to save, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        raw_text = summary.get("raw_summary", json.dumps(summary))
        try:
            index_meeting_notes(state, raw_text)
        except Exception:
            logger.warning("Failed to index meeting notes", exc_info=True)

        return {
            "meeting_summaries": state.get("meeting_summaries", []) + [
                {"type": "meeting_summary", "content": summary}
            ],
            "last_node": "summarize_meeting",
        }

    return {"last_node": "summarize_meeting", "error": "Meeting summary rejected by FDE"}
