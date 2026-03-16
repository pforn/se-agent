from src.graph.state import CustomerState


async def create_demo_script(state: CustomerState) -> dict:
    """Demo walkthrough using customer's specifics. interrupt()."""
    return {"last_node": "create_demo_script"}
