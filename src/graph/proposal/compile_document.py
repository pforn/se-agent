import logging

from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.integrations.gdrive import get_gdrive_client

logger = logging.getLogger(__name__)

SECTION_ORDER = ["proposal_narrative", "reference_architecture", "deployment_plan"]


def _assemble_proposal(state: CustomerState) -> str:
    docs = state.get("generated_docs", [])
    sections = []
    for doc_type in SECTION_ORDER:
        for doc in reversed(docs):
            if doc.get("type") == doc_type:
                sections.append(doc.get("content", ""))
                break
    return "\n\n---\n\n".join(sections)


def _upload_to_gdrive(title: str, content: str) -> str | None:
    client = get_gdrive_client()
    if client is None:
        return None
    try:
        return client.create_doc(title, content)
    except Exception:
        logger.warning("Failed to upload proposal to Google Drive", exc_info=True)
        return None


async def compile_document(state: CustomerState) -> dict:
    compiled_text = _assemble_proposal(state)

    decision = interrupt({
        "type": "review_compiled_proposal",
        "document": compiled_text,
        "customer": state.get("customer_name", ""),
        "instructions": "Review the full compiled proposal. Approve to upload to Google Drive, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        title = f"Proposal — {state.get('customer_name', 'Unknown')}"
        gdrive_url = _upload_to_gdrive(title, compiled_text)

        doc_record = {
            "type": "compiled_proposal",
            "title": title,
            "content": compiled_text,
            "gdrive_url": gdrive_url,
            "created_at": state.get("updated_at", ""),
        }
        return {
            "generated_docs": state.get("generated_docs", []) + [doc_record],
            "last_node": "compile_document",
        }

    return {"last_node": "compile_document", "error": "Compiled proposal rejected by FDE"}
