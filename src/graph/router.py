from langgraph.graph import END, StateGraph

from src.graph.discovery import build_discovery_subgraph
from src.graph.followup import build_followup_subgraph
from src.graph.poc import build_poc_subgraph
from src.graph.proposal import build_proposal_subgraph
from src.graph.state import CustomerState


async def intake_classifier(state: CustomerState) -> dict:
    """Route to the appropriate subgraph based on customer phase.

    In production this will be a Haiku call that reads the trigger + current phase.
    For now, routes directly based on the phase field.
    """
    return {"last_node": "intake_classifier"}


def route_by_phase(state: CustomerState) -> str:
    phase = state.get("phase", "discovery")
    phase_map = {
        "discovery": "discovery_subgraph",
        "poc": "poc_subgraph",
        "proposal": "proposal_subgraph",
        "followup": "followup_subgraph",
    }
    return phase_map.get(phase, "discovery_subgraph")


def build_router_graph() -> StateGraph:
    graph = StateGraph(CustomerState)

    graph.add_node("intake_classifier", intake_classifier)
    graph.add_node("discovery_subgraph", build_discovery_subgraph().compile())
    graph.add_node("poc_subgraph", build_poc_subgraph().compile())
    graph.add_node("proposal_subgraph", build_proposal_subgraph().compile())
    graph.add_node("followup_subgraph", build_followup_subgraph().compile())

    graph.set_entry_point("intake_classifier")
    graph.add_conditional_edges("intake_classifier", route_by_phase)

    graph.add_edge("discovery_subgraph", END)
    graph.add_edge("poc_subgraph", END)
    graph.add_edge("proposal_subgraph", END)
    graph.add_edge("followup_subgraph", END)

    return graph
