from src.graph.state import CustomerState, TechnicalEnvironment


def test_customer_state_construction():
    state: CustomerState = {
        "customer_id": "acme-corp",
        "customer_name": "Acme Corp",
        "phase": "discovery",
        "tech_env": TechnicalEnvironment(
            current_warehouse="Snowflake Enterprise",
            compute_engines=["Spark 3.5", "dbt-core 1.8"],
            cloud_provider="aws",
            pain_points=["Snowflake costs 3x YoY", "dbt runs > 4hrs"],
        ),
        "use_cases": [],
        "stakeholders": [],
        "metrics": None,
        "economic_buyer": None,
        "decision_criteria": [],
        "decision_process": None,
        "identified_pain": [],
        "champion": None,
        "health_score": None,
        "messages": [],
        "action_items": [],
        "product_feedback": [],
        "competitive_intel": [],
        "meeting_summaries": [],
        "generated_docs": [],
        "pending_approval": None,
        "last_node": None,
        "error": None,
        "created_at": "2026-03-16T00:00:00Z",
        "updated_at": "2026-03-16T00:00:00Z",
    }
    assert state["customer_id"] == "acme-corp"
    assert state["tech_env"]["current_warehouse"] == "Snowflake Enterprise"
    assert state["phase"] == "discovery"
