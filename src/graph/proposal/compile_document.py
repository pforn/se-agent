from src.graph.state import CustomerState


async def compile_document(state: CustomerState) -> dict:
    """Assemble into Google Doc via Docs API. Tool node (no LLM). interrupt()."""
    return {"last_node": "compile_document"}
