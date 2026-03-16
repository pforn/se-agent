import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.discovery import GATHER_CONTEXT_PROMPT
from src.llm.prompts.system_fde import FDE_ROLE_CONTEXT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT


async def gather_context(state: CustomerState) -> dict:
    """Extract TechnicalEnvironment + Stakeholders from emails/notes. Auto (no interrupt)."""
    llm = get_llm("strong")

    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""

    existing_tech_env = state.get("tech_env", {})
    existing_stakeholders = state.get("stakeholders", [])
    existing_context = ""
    if existing_tech_env or existing_stakeholders:
        existing_context = (
            f"Existing technical environment (update, don't overwrite unless correcting):\n"
            f"{json.dumps(existing_tech_env, indent=2)}\n\n"
            f"Existing stakeholders (update/add, don't remove):\n"
            f"{json.dumps(existing_stakeholders, indent=2)}"
        )

    prompt = GATHER_CONTEXT_PROMPT.format(
        email_content=last_message,
        existing_context=existing_context,
    )

    response = await llm.ainvoke([
        SystemMessage(content=f"{TOWER_SYSTEM_CONTEXT}\n\n{FDE_ROLE_CONTEXT}"),
        HumanMessage(content=prompt),
    ])

    try:
        extracted = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            extracted = json.loads(content[start:end])
        else:
            return {"last_node": "gather_context", "error": "Failed to parse gather_context response"}

    result: dict = {"last_node": "gather_context"}

    if "tech_env" in extracted:
        merged_env = {**existing_tech_env, **extracted["tech_env"]}
        result["tech_env"] = merged_env

    if "stakeholders" in extracted:
        existing_names = {s["name"] for s in existing_stakeholders}
        merged = list(existing_stakeholders)
        for s in extracted["stakeholders"]:
            if s.get("name") not in existing_names:
                merged.append(s)
        result["stakeholders"] = merged

    return result
