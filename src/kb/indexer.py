from __future__ import annotations

import json

from src.kb.store import get_kb_store


def _doc_id(prefix: str, customer_id: str, suffix: str = "") -> str:
    return f"{prefix}:{customer_id}:{suffix}" if suffix else f"{prefix}:{customer_id}"


def _base_metadata(state: dict) -> dict:
    meta = {
        "customer_id": state.get("customer_id", ""),
        "customer_name": state.get("customer_name", ""),
        "phase": state.get("phase", ""),
    }
    cloud = state.get("tech_env", {}).get("cloud_provider")
    if cloud:
        meta["cloud_provider"] = cloud
    return meta


def index_discovery_summary(state: dict, doc_content: str) -> None:
    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")
    meta = _base_metadata(state)
    meta["created_at"] = state.get("updated_at", "")
    store.add_document(
        collection_name="discovery_summaries",
        doc_id=_doc_id("ds", customer_id),
        text=doc_content,
        metadata=meta,
    )


def index_stack_analysis(state: dict) -> None:
    analysis = None
    for summary in state.get("meeting_summaries", []):
        if summary.get("type") == "stack_analysis":
            analysis = summary["content"]
            break

    if analysis is None:
        return

    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")
    meta = _base_metadata(state)
    meta["created_at"] = state.get("updated_at", "")
    store.add_document(
        collection_name="stack_analyses",
        doc_id=_doc_id("sa", customer_id),
        text=json.dumps(analysis, indent=2),
        metadata=meta,
    )


def index_use_cases(state: dict) -> None:
    use_cases = state.get("use_cases", [])
    if not use_cases:
        return

    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")

    for i, uc in enumerate(use_cases):
        meta = _base_metadata(state)
        meta["tower_fit"] = uc.get("tower_fit", "unknown")
        meta["use_case_name"] = uc.get("name", "")
        meta["created_at"] = state.get("updated_at", "")

        text = f"{uc['name']}: {uc['description']}"
        if uc.get("notes"):
            text += f"\n{uc['notes']}"
        if uc.get("data_sources"):
            text += f"\nData sources: {', '.join(uc['data_sources'])}"
        if uc.get("current_solution"):
            text += f"\nCurrent solution: {uc['current_solution']}"

        store.add_document(
            collection_name="use_cases",
            doc_id=_doc_id("uc", customer_id, str(i)),
            text=text,
            metadata=meta,
        )


def index_meeting_notes(state: dict, summary_content: str) -> None:
    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")
    meeting_index = len(state.get("meeting_summaries", []))
    meta = _base_metadata(state)
    meta["created_at"] = state.get("updated_at", "")
    store.add_document(
        collection_name="meeting_notes",
        doc_id=_doc_id("mn", customer_id, str(meeting_index)),
        text=summary_content,
        metadata=meta,
    )


def index_competitive_intel(state: dict) -> None:
    intel_list = state.get("competitive_intel", [])
    if not intel_list:
        return

    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")

    for i, item in enumerate(intel_list):
        meta = _base_metadata(state)
        meta["competitor"] = item.get("competitor", "")
        meta["created_at"] = item.get("created_at", state.get("updated_at", ""))

        text = f"[{item.get('competitor', '')}] {item.get('claim', '')}"
        if item.get("tower_response"):
            text += f"\nTower response: {item['tower_response']}"
        if item.get("source"):
            text += f"\nSource: {item['source']}"

        store.add_document(
            collection_name="competitive_intel",
            doc_id=_doc_id("ci", customer_id, str(i)),
            text=text,
            metadata=meta,
        )


def index_product_feedback(state: dict) -> None:
    feedback_list = state.get("product_feedback", [])
    if not feedback_list:
        return

    store = get_kb_store()
    customer_id = state.get("customer_id", "unknown")

    for i, fb in enumerate(feedback_list):
        meta = _base_metadata(state)
        meta["severity"] = fb.get("severity", "unknown")
        meta["feature_area"] = fb.get("feature_area", "")
        meta["created_at"] = fb.get("created_at", state.get("updated_at", ""))

        text = f"[{fb.get('feature_area', '')}] {fb.get('description', '')}"
        if fb.get("customer"):
            text += f"\nCustomer: {fb['customer']}"

        store.add_document(
            collection_name="competitive_intel",
            doc_id=_doc_id("pf", customer_id, str(i)),
            text=text,
            metadata=meta,
        )
