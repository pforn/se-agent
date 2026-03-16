from src.graph.state import CustomerState


async def extract_product_feedback(state: CustomerState) -> dict:
    """Feature requests, bugs, capability gaps. Tagged by area + severity. interrupt()."""
    return {"last_node": "extract_product_feedback"}
