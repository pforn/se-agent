from src.graph.state import CustomerState


async def generate_poc_plan(state: CustomerState) -> dict:
    """Concrete PoC scope: pipelines, data, success criteria, timeline. interrupt()."""
    return {"last_node": "generate_poc_plan"}
