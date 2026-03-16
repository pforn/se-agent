import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.discovery import SCORE_QUALIFICATION_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT


async def score_qualification(state: CustomerState) -> dict:
    """Compute MEDDIC fields + health_score. interrupt() for FDE review."""
    llm = get_llm("fast")

    tech_env = state.get("tech_env", {})
    prompt = SCORE_QUALIFICATION_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        tech_env_json=json.dumps(tech_env, indent=2),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        pain_points_json=json.dumps(tech_env.get("pain_points", []), indent=2),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        qualification = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            qualification = json.loads(content[start:end])
        else:
            return {"last_node": "score_qualification", "error": "Failed to parse qualification response"}

    decision = interrupt({
        "type": "review_qualification",
        "qualification": qualification,
        "customer": state.get("customer_name", ""),
        "instructions": "Review MEDDIC scoring and health score. Approve or edit.",
    })

    action = decision.get("action", "approve")
    if action == "edit":
        qualification = {**qualification, **decision.get("overrides", {})}

    result: dict = {"last_node": "score_qualification"}
    for field in ("metrics", "economic_buyer", "decision_criteria", "decision_process",
                  "identified_pain", "champion", "health_score"):
        if field in qualification:
            result[field] = qualification[field]
    return result
