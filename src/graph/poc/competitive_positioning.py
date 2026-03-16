from src.graph.state import CustomerState


async def competitive_positioning(state: CustomerState) -> dict:
    """Generate competitive comparison via Tavily + KB. interrupt()."""
    return {"last_node": "competitive_positioning"}
