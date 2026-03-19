import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.integrations.gdrive import get_gdrive_client
from src.llm.models import get_llm
from src.llm.prompts.followup import DRAFT_FOLLOWUP_EMAIL_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _get_latest_summary(state: CustomerState) -> str:
    for s in reversed(state.get("meeting_summaries", [])):
        if s.get("type") == "meeting_summary":
            content = s.get("content", {})
            return content.get("raw_summary", json.dumps(content, indent=2))
    return ""


def _upload_to_gdrive(title: str, content: str) -> str | None:
    client = get_gdrive_client()
    if client is None:
        return None
    try:
        return client.create_doc(title, content)
    except Exception:
        logger.warning("Failed to upload to Google Drive", exc_info=True)
        return None


async def draft_followup_email(state: CustomerState) -> dict:
    llm = get_llm("strong")

    meeting_summary = _get_latest_summary(state)

    prompt = DRAFT_FOLLOWUP_EMAIL_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        meeting_summary=meeting_summary,
        action_items_json=json.dumps(state.get("action_items", []), indent=2),
        product_feedback_json=json.dumps(state.get("product_feedback", []), indent=2),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    email_text = response.content

    decision = interrupt({
        "type": "approve_followup_email",
        "document": email_text,
        "customer": state.get("customer_name", ""),
        "instructions": "Review follow-up email. Approve to send/save, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        title = f"Follow-up — {state.get('customer_name', 'Unknown')}"
        gdrive_url = _upload_to_gdrive(title, email_text)

        doc_record = {
            "type": "followup_email",
            "title": title,
            "content": email_text,
            "gdrive_url": gdrive_url,
            "created_at": state.get("updated_at", ""),
        }
        return {
            "generated_docs": state.get("generated_docs", []) + [doc_record],
            "last_node": "draft_followup_email",
        }
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Please revise the email with these changes:\n{revision_instructions}"),
        ])
        revised_text = revised.content

        decision2 = interrupt({
            "type": "approve_followup_email",
            "document": revised_text,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised follow-up email. Approve or reject.",
        })

        if decision2.get("action") == "approve":
            title = f"Follow-up — {state.get('customer_name', 'Unknown')}"
            gdrive_url = _upload_to_gdrive(title, revised_text)

            doc_record = {
                "type": "followup_email",
                "title": title,
                "content": revised_text,
                "gdrive_url": gdrive_url,
                "created_at": state.get("updated_at", ""),
            }
            return {
                "generated_docs": state.get("generated_docs", []) + [doc_record],
                "last_node": "draft_followup_email",
            }

    return {"last_node": "draft_followup_email", "error": "Follow-up email rejected by FDE"}
