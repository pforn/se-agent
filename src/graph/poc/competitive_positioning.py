import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.integrations.tavily_search import get_tavily_client
from src.kb.indexer import index_competitive_intel
from src.kb.store import get_kb_store
from src.llm.models import get_llm
from src.llm.prompts.poc import COMPETITIVE_POSITIONING_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT

logger = logging.getLogger(__name__)


def _identify_competitor(state: CustomerState) -> str:
    warehouse = state.get("tech_env", {}).get("current_warehouse", "")
    if not warehouse:
        return "Snowflake"
    for name in ("Snowflake", "Databricks", "BigQuery", "Redshift"):
        if name.lower() in warehouse.lower():
            return name
    return warehouse


def _run_tavily_research(competitor: str, customer_name: str) -> str:
    client = get_tavily_client()
    if client is None:
        return "No web research available (Tavily not configured)."

    queries = [
        f"Tower data platform vs {competitor} comparison 2026",
        f"{competitor} Apache Iceberg limitations migration",
    ]
    all_results = []
    for q in queries:
        all_results.extend(client.search(q, max_results=3))

    if not all_results:
        return "No web research results found."

    sections = []
    for r in all_results:
        sections.append(f"### {r['title']}\nURL: {r['url']}\n{r['content'][:500]}")
    return "\n\n".join(sections)


def _get_kb_intel(competitor: str) -> str:
    try:
        store = get_kb_store()
        results = store.retrieve_similar(
            "competitive_intel",
            f"{competitor} Tower comparison",
            n_results=5,
        )
        if not results:
            return "No existing competitive intelligence in KB."
        sections = []
        for r in results:
            sections.append(f"- {r['text'][:300]}")
        return "\n".join(sections)
    except Exception:
        logger.debug("KB not available for competitive intel retrieval")
        return "KB not available."


async def competitive_positioning(state: CustomerState) -> dict:
    llm = get_llm("strong")

    competitor = _identify_competitor(state)
    research_results = _run_tavily_research(competitor, state.get("customer_name", ""))
    kb_intel = _get_kb_intel(competitor)

    tech_env = state.get("tech_env", {})
    data_volume = tech_env.get("data_volume_tb", "unknown")

    prompt = COMPETITIVE_POSITIONING_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        competitor=competitor,
        research_results=research_results,
        kb_competitive_intel=kb_intel,
        tech_env_json=json.dumps(tech_env, indent=2),
        decision_criteria_json=json.dumps(state.get("decision_criteria", []), indent=2),
        pain_points_json=json.dumps(state.get("identified_pain", []), indent=2),
        data_volume_tb=data_volume,
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
            return {"last_node": "competitive_positioning", "error": "Failed to parse competitive analysis"}

    decision = interrupt({
        "type": "review_competitive_positioning",
        "analysis": analysis,
        "competitor": competitor,
        "customer": state.get("customer_name", ""),
        "instructions": "Review competitive positioning. Approve or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        return _build_approve_result(state, analysis, competitor)

    return {"last_node": "competitive_positioning", "error": "Competitive positioning rejected by FDE"}


def _build_approve_result(state: CustomerState, analysis: dict, competitor: str) -> dict:
    raw_items = analysis.get("competitive_intel_items", [])
    created_at = state.get("updated_at", "")
    new_intel = []
    for item in raw_items:
        new_intel.append({
            "competitor": item.get("competitor", competitor),
            "claim": item.get("claim", ""),
            "tower_response": item.get("tower_response", ""),
            "source": item.get("source", ""),
            "created_at": created_at,
        })

    merged_intel = state.get("competitive_intel", []) + new_intel

    doc_record = {
        "type": "competitive_positioning",
        "title": f"Competitive Positioning: Tower vs {competitor} — {state.get('customer_name', 'Unknown')}",
        "content": json.dumps(analysis, indent=2),
        "gdrive_url": None,
        "created_at": created_at,
    }

    result_state = {
        "competitive_intel": merged_intel,
        "generated_docs": state.get("generated_docs", []) + [doc_record],
        "last_node": "competitive_positioning",
    }

    try:
        index_competitive_intel({**state, **result_state})
    except Exception:
        logger.warning("Failed to index competitive intel", exc_info=True)

    return result_state
