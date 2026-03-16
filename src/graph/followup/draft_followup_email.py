from src.graph.state import CustomerState


async def draft_followup_email(state: CustomerState) -> dict:
    """Follow-up email with summary, action items, next steps. interrupt()."""
    return {"last_node": "draft_followup_email"}
