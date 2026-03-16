import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.discovery import ANALYZE_STACK_PROMPT
from src.llm.prompts.system_tower import (
    TOWER_SYSTEM_CONTEXT,
    load_iceberg_patterns,
    load_tower_knowledge,
)


async def analyze_stack(state: CustomerState) -> dict:
    """Match tech stack against KB for similar customers and known issues. Auto (no interrupt)."""
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    stakeholders = state.get("stakeholders", [])

    prompt = ANALYZE_STACK_PROMPT.format(
        tower_knowledge=load_tower_knowledge(),
        iceberg_patterns=load_iceberg_patterns(),
        tech_env_json=json.dumps(tech_env, indent=2),
        stakeholders_json=json.dumps(stakeholders, indent=2),
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    try:
        analysis = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            analysis = json.loads(content[start:end])
        else:
            analysis = {"raw_analysis": response.content}

    return {
        "last_node": "analyze_stack",
        "meeting_summaries": state.get("meeting_summaries", []) + [
            {"type": "stack_analysis", "content": analysis}
        ],
    }
