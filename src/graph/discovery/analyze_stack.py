import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import CustomerState
from src.kb.indexer import index_stack_analysis as _index_sa
from src.kb.store import get_kb_store
from src.llm.models import get_llm
from src.llm.prompts.discovery import ANALYZE_STACK_PROMPT
from src.llm.prompts.system_tower import (
    TOWER_SYSTEM_CONTEXT,
    load_iceberg_patterns,
    load_tower_knowledge,
)

logger = logging.getLogger(__name__)


def _build_similar_contexts(tech_env: dict) -> str:
    try:
        store = get_kb_store()
    except Exception:
        logger.debug("KB not available, skipping similar context retrieval")
        return "No previous customer data available yet."

    cloud = tech_env.get("cloud_provider")
    warehouse = tech_env.get("current_warehouse", "")
    query = f"{warehouse} {cloud or ''} data platform migration".strip()

    where_filter = {"cloud_provider": cloud} if cloud else None

    stack_results = store.retrieve_similar(
        "stack_analyses", query, n_results=3, where=where_filter
    )
    discovery_results = store.retrieve_similar(
        "discovery_summaries", query, n_results=2
    )

    if not stack_results and not discovery_results:
        return "No previous customer data available yet."

    sections = []
    for r in stack_results:
        customer = r["metadata"].get("customer_name", "Unknown")
        sections.append(f"### {customer} (stack analysis)\n{r['text']}")
    for r in discovery_results:
        customer = r["metadata"].get("customer_name", "Unknown")
        sections.append(f"### {customer} (discovery summary)\n{r['text'][:500]}")

    return "\n\n".join(sections)


async def analyze_stack(state: CustomerState) -> dict:
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    stakeholders = state.get("stakeholders", [])

    similar_contexts = _build_similar_contexts(tech_env)

    prompt = ANALYZE_STACK_PROMPT.format(
        tower_knowledge=load_tower_knowledge(),
        iceberg_patterns=load_iceberg_patterns(),
        similar_contexts=similar_contexts,
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

    result_state = {
        "last_node": "analyze_stack",
        "meeting_summaries": state.get("meeting_summaries", []) + [
            {"type": "stack_analysis", "content": analysis}
        ],
    }

    try:
        _index_sa({**state, **result_state})
    except Exception:
        logger.warning("Failed to index stack analysis", exc_info=True)

    return result_state
