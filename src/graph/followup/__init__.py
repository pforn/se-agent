from langgraph.graph import StateGraph

from src.graph.state import CustomerState

from .draft_followup_email import draft_followup_email
from .extract_action_items import extract_action_items
from .extract_product_feedback import extract_product_feedback
from .summarize_meeting import summarize_meeting
from .update_health_score import update_health_score


def build_followup_subgraph() -> StateGraph:
    sg = StateGraph(CustomerState)
    sg.add_node("summarize_meeting", summarize_meeting)
    sg.add_node("extract_action_items", extract_action_items)
    sg.add_node("extract_product_feedback", extract_product_feedback)
    sg.add_node("update_health_score", update_health_score)
    sg.add_node("draft_followup_email", draft_followup_email)

    sg.set_entry_point("summarize_meeting")
    sg.add_edge("summarize_meeting", "extract_action_items")
    sg.add_edge("extract_action_items", "extract_product_feedback")
    sg.add_edge("extract_product_feedback", "update_health_score")
    sg.add_edge("update_health_score", "draft_followup_email")
    sg.set_finish_point("draft_followup_email")
    return sg
