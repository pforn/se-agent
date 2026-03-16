from langgraph.graph import StateGraph

from src.graph.state import CustomerState

from .competitive_positioning import competitive_positioning
from .create_demo_script import create_demo_script
from .design_architecture import design_architecture
from .generate_poc_plan import generate_poc_plan


def build_poc_subgraph() -> StateGraph:
    sg = StateGraph(CustomerState)
    sg.add_node("design_architecture", design_architecture)
    sg.add_node("generate_poc_plan", generate_poc_plan)
    sg.add_node("competitive_positioning", competitive_positioning)
    sg.add_node("create_demo_script", create_demo_script)

    sg.set_entry_point("design_architecture")
    sg.add_edge("design_architecture", "generate_poc_plan")
    sg.add_edge("generate_poc_plan", "competitive_positioning")
    sg.add_edge("competitive_positioning", "create_demo_script")
    sg.set_finish_point("create_demo_script")
    return sg
