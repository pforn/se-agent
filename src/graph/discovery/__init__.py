from langgraph.graph import StateGraph

from src.graph.state import CustomerState

from .analyze_stack import analyze_stack
from .gather_context import gather_context
from .generate_discovery_summary import generate_discovery_summary
from .identify_use_cases import identify_use_cases
from .score_qualification import score_qualification


def build_discovery_subgraph() -> StateGraph:
    sg = StateGraph(CustomerState)
    sg.add_node("gather_context", gather_context)
    sg.add_node("analyze_stack", analyze_stack)
    sg.add_node("identify_use_cases", identify_use_cases)
    sg.add_node("score_qualification", score_qualification)
    sg.add_node("generate_discovery_summary", generate_discovery_summary)

    sg.set_entry_point("gather_context")
    sg.add_edge("gather_context", "analyze_stack")
    sg.add_edge("analyze_stack", "identify_use_cases")
    sg.add_edge("identify_use_cases", "score_qualification")
    sg.add_edge("score_qualification", "generate_discovery_summary")
    sg.set_finish_point("generate_discovery_summary")
    return sg
