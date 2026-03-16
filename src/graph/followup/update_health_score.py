from src.graph.state import CustomerState


async def update_health_score(state: CustomerState) -> dict:
    """Recompute health_score from engagement signals. Auto (no interrupt)."""
    return {"last_node": "update_health_score"}
