import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.discovery import IDENTIFY_USE_CASES_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT, load_tower_knowledge


async def identify_use_cases(state: CustomerState) -> dict:
    """Propose UseCase entries with tower_fit assessments. interrupt() for FDE review."""
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    pain_points = tech_env.get("pain_points", [])

    stack_analysis = ""
    for summary in state.get("meeting_summaries", []):
        if summary.get("type") == "stack_analysis":
            stack_analysis = json.dumps(summary["content"], indent=2)
            break

    prompt = IDENTIFY_USE_CASES_PROMPT.format(
        tech_env_json=json.dumps(tech_env, indent=2),
        pain_points_json=json.dumps(pain_points, indent=2),
        stack_analysis=stack_analysis,
        tower_knowledge=load_tower_knowledge(),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        use_cases = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            use_cases = json.loads(content[start:end])
        else:
            use_cases = []

    if not isinstance(use_cases, list):
        use_cases = [use_cases]

    decision = interrupt({
        "type": "review_use_cases",
        "use_cases": use_cases,
        "customer": state.get("customer_name", ""),
        "instructions": "Review proposed use cases. Approve, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return {"use_cases": use_cases, "last_node": "identify_use_cases"}
    elif action == "edit":
        edited = decision.get("use_cases", use_cases)
        return {"use_cases": edited, "last_node": "identify_use_cases"}
    else:
        return {"last_node": "identify_use_cases", "error": "Use cases rejected by FDE"}
