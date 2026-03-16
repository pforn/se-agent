from src.graph.state import CustomerState


async def draft_proposal(state: CustomerState) -> dict:
    """Narrative proposal: problem, solution, outcomes. interrupt()."""
    return {"last_node": "draft_proposal"}
