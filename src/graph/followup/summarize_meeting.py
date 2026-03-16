from src.graph.state import CustomerState


async def summarize_meeting(state: CustomerState) -> dict:
    """Structured summary from raw notes/transcript. interrupt()."""
    return {"last_node": "summarize_meeting"}
