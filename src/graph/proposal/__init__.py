from langgraph.graph import StateGraph

from src.graph.state import CustomerState

from .add_deployment_plan import add_deployment_plan
from .add_reference_architecture import add_reference_architecture
from .compile_document import compile_document
from .draft_proposal import draft_proposal


def build_proposal_subgraph() -> StateGraph:
    sg = StateGraph(CustomerState)
    sg.add_node("draft_proposal", draft_proposal)
    sg.add_node("add_reference_architecture", add_reference_architecture)
    sg.add_node("add_deployment_plan", add_deployment_plan)
    sg.add_node("compile_document", compile_document)

    sg.set_entry_point("draft_proposal")
    sg.add_edge("draft_proposal", "add_reference_architecture")
    sg.add_edge("add_reference_architecture", "add_deployment_plan")
    sg.add_edge("add_deployment_plan", "compile_document")
    sg.set_finish_point("compile_document")
    return sg
