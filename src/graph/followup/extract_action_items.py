from src.graph.state import CustomerState


async def extract_action_items(state: CustomerState) -> dict:
    """Identify action items, assign owners. interrupt()."""
    return {"last_node": "extract_action_items"}
