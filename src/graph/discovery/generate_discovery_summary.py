import json

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.graph.state import CustomerState
from src.llm.models import get_llm
from src.llm.prompts.discovery import GENERATE_DISCOVERY_SUMMARY_PROMPT
from src.llm.prompts.system_tower import TOWER_SYSTEM_CONTEXT


async def generate_discovery_summary(state: CustomerState) -> dict:
    """Generate formatted discovery doc. interrupt() before writing to GDrive."""
    llm = get_llm("strong")

    tech_env = state.get("tech_env", {})
    stack_analysis = ""
    for summary in state.get("meeting_summaries", []):
        if summary.get("type") == "stack_analysis":
            stack_analysis = json.dumps(summary["content"], indent=2)
            break

    qualification = {
        "metrics": state.get("metrics"),
        "economic_buyer": state.get("economic_buyer"),
        "decision_criteria": state.get("decision_criteria", []),
        "decision_process": state.get("decision_process"),
        "identified_pain": state.get("identified_pain", []),
        "champion": state.get("champion"),
        "health_score": state.get("health_score"),
    }

    prompt = GENERATE_DISCOVERY_SUMMARY_PROMPT.format(
        customer_name=state.get("customer_name", "Unknown"),
        tech_env_json=json.dumps(tech_env, indent=2),
        stakeholders_json=json.dumps(state.get("stakeholders", []), indent=2),
        use_cases_json=json.dumps(state.get("use_cases", []), indent=2),
        qualification_json=json.dumps(qualification, indent=2),
        stack_analysis=stack_analysis,
    )

    response = await llm.ainvoke([
        SystemMessage(content=TOWER_SYSTEM_CONTEXT),
        HumanMessage(content=prompt),
    ])

    summary_doc = response.content

    decision = interrupt({
        "type": "approve_discovery_summary",
        "document": summary_doc,
        "customer": state.get("customer_name", ""),
        "instructions": "Review discovery summary. Approve to save to Google Drive, edit, or reject.",
    })

    action = decision.get("action", "approve")
    if action == "approve":
        doc_record = {
            "type": "discovery_summary",
            "title": f"Discovery Summary — {state.get('customer_name', 'Unknown')}",
            "content": summary_doc,
            "gdrive_url": None,
            "created_at": state.get("updated_at", ""),
        }
        return {
            "generated_docs": state.get("generated_docs", []) + [doc_record],
            "last_node": "generate_discovery_summary",
        }
    elif action == "edit":
        revision_instructions = decision.get("edits", "")
        revised = await llm.ainvoke([
            SystemMessage(content=TOWER_SYSTEM_CONTEXT),
            HumanMessage(content=prompt),
            response,
            HumanMessage(content=f"Please revise the summary with these changes:\n{revision_instructions}"),
        ])
        revised_doc = revised.content

        decision2 = interrupt({
            "type": "approve_discovery_summary",
            "document": revised_doc,
            "customer": state.get("customer_name", ""),
            "instructions": "Review revised discovery summary. Approve or reject.",
        })

        if decision2.get("action") == "approve":
            doc_record = {
                "type": "discovery_summary",
                "title": f"Discovery Summary — {state.get('customer_name', 'Unknown')}",
                "content": revised_doc,
                "gdrive_url": None,
                "created_at": state.get("updated_at", ""),
            }
            return {
                "generated_docs": state.get("generated_docs", []) + [doc_record],
                "last_node": "generate_discovery_summary",
            }

    return {"last_node": "generate_discovery_summary", "error": "Discovery summary rejected by FDE"}
