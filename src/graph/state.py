from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TechnicalEnvironment(TypedDict, total=False):
    current_warehouse: str | None
    compute_engines: list[str]
    storage_layer: str | None
    table_format: str | None
    catalog: str | None
    orchestrator: str | None
    data_volume_tb: float | None
    daily_ingestion_gb: float | None
    query_engines: list[str]
    source_systems: list[str]
    cloud_provider: Literal["aws", "gcp", "azure", "multi"] | None
    governance_tools: list[str]
    pain_points: list[str]
    migration_status: str | None


class UseCase(TypedDict):
    name: str
    description: str
    data_sources: list[str]
    target_consumers: list[str]
    latency_requirement: str | None
    current_solution: str | None
    tower_fit: Literal["strong", "moderate", "weak", "unknown"]
    notes: str


class Stakeholder(TypedDict):
    name: str
    role: str
    influence: Literal["champion", "evaluator", "blocker", "end_user"]
    sentiment: Literal["positive", "neutral", "skeptical", "unknown"]
    notes: str


class ActionItem(TypedDict):
    description: str
    owner: Literal["fde", "customer", "tower_eng"]
    due_date: str | None
    status: Literal["open", "in_progress", "done", "blocked"]
    created_at: str


class ProductFeedback(TypedDict):
    feature_area: str
    description: str
    customer: str
    severity: Literal["blocker", "important", "nice_to_have"]
    created_at: str
    ticket_url: str | None


class CompetitiveIntel(TypedDict):
    competitor: str
    claim: str
    tower_response: str
    source: str
    created_at: str


class CustomerState(TypedDict):
    # Identity
    customer_id: str
    customer_name: str
    phase: Literal["discovery", "poc", "proposal", "followup", "closed_won", "closed_lost"]

    # Technical Environment
    tech_env: TechnicalEnvironment
    use_cases: list[UseCase]

    # People
    stakeholders: list[Stakeholder]

    # Qualification (MEDDIC-adapted)
    metrics: str | None
    economic_buyer: str | None
    decision_criteria: list[str]
    decision_process: str | None
    identified_pain: list[str]
    champion: str | None
    health_score: int | None

    # Work Products
    messages: Annotated[list[AnyMessage], add_messages]
    action_items: list[ActionItem]
    product_feedback: list[ProductFeedback]
    competitive_intel: list[CompetitiveIntel]
    meeting_summaries: list[dict]
    generated_docs: list[dict]

    # Agent Internals
    pending_approval: dict | None
    last_node: str | None
    error: str | None
    created_at: str
    updated_at: str
