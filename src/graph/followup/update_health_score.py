import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.followup import UPDATE_HEALTH_SCORE_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


async def update_health_score(state: CustomerState) -> dict:
    llm = get_llm("fast")

    qualification = {
        "metrics": state.get("metrics"),
        "economic_buyer": state.get("economic_buyer"),
        "decision_criteria": state.get("decision_criteria", []),
        "decision_process": state.get("decision_process"),
        "identified_pain": state.get("identified_pain", []),
        "champion": state.get("champion"),
    }

    prompt = UPDATE_HEALTH_SCORE_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        qualification_json=json.dumps(qualification, indent=2),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        action_items_json=json.dumps(state.get("action_items", []), indent=2),
        meeting_count=len(state.get("meeting_summaries", [])),
        current_health_score=state.get("health_score", "None"),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
        else:
            return {"last_node": "update_health_score", "error": "Failed to parse health score response"}

    new_score = result.get("health_score", state.get("health_score"))

    # Persist to DB (graceful degradation — DB failure doesn't break the graph)
    try:
        from src.config import settings
        from src.db.app_db import save_health_score

        customer_id = state.get("customer_id")
        if customer_id and new_score is not None:
            save_health_score(settings.app_db_path, customer_id, new_score)
    except Exception:
        logger.warning("Failed to persist health score to DB", exc_info=True)

    return {
        "health_score": new_score,
        "last_node": "update_health_score",
    }

