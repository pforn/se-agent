import tempfile
from pathlib import Path

from src.db.app_db import (
    get_audit_log,
    get_dashboard_stats,
    get_feedback_summary,
    get_health_score_history,
    init_db,
    list_customers,
    list_product_feedback,
    log_audit,
    save_health_score,
    save_product_feedback,
    upsert_customer,
)


def test_init_and_crud():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)

        assert list_customers(db_path) == []

        upsert_customer(db_path, "acme-corp", "Acme Corp")
        customers = list_customers(db_path)
        assert len(customers) == 1
        assert customers[0]["customer_id"] == "acme-corp"
        assert customers[0]["phase"] == "discovery"

        upsert_customer(db_path, "acme-corp", "Acme Corp", phase="poc")
        customers = list_customers(db_path)
        assert len(customers) == 1
        assert customers[0]["phase"] == "poc"


def test_audit_log():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")
        log_audit(db_path, "acme-corp", "approved", node_name="generate_discovery_summary")


def test_save_and_get_health_score_history():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")

        save_health_score(db_path, "acme-corp", 45)
        save_health_score(db_path, "acme-corp", 60)
        save_health_score(db_path, "acme-corp", 72)

        history = get_health_score_history(db_path, "acme-corp")
        assert len(history) == 3
        # Oldest first
        assert history[0]["score"] == 45
        assert history[2]["score"] == 72
        # Verify customer record updated
        customers = list_customers(db_path)
        assert customers[0]["health_score"] == 72


def test_get_audit_log():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")

        log_audit(db_path, "acme-corp", "approved", node_name="gather_context")
        log_audit(db_path, "acme-corp", "rejected", node_name="analyze_stack", details="Needs more detail")
        log_audit(db_path, "acme-corp", "approved", node_name="generate_discovery_summary")

        entries = get_audit_log(db_path, "acme-corp")
        assert len(entries) == 3
        # Most recent first
        assert entries[0]["node_name"] == "generate_discovery_summary"
        assert entries[1]["details"] == "Needs more detail"


def test_product_feedback_crud():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")

        feedback = [
            {"feature_area": "catalog", "description": "Need Hive Metastore support", "severity": "blocker"},
            {"feature_area": "ingestion", "description": "Kafka connector improvements", "severity": "important"},
        ]
        save_product_feedback(db_path, "acme-corp", feedback)

        result = list_product_feedback(db_path, "acme-corp")
        assert len(result) == 2
        assert result[0]["feature_area"] in ("catalog", "ingestion")

        # All feedback
        all_fb = list_product_feedback(db_path)
        assert len(all_fb) == 2


def test_get_feedback_summary():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")
        upsert_customer(db_path, "beta-inc", "Beta Inc")

        save_product_feedback(db_path, "acme-corp", [
            {"feature_area": "catalog", "description": "HMS", "severity": "blocker"},
            {"feature_area": "catalog", "description": "Glue", "severity": "important"},
        ])
        save_product_feedback(db_path, "beta-inc", [
            {"feature_area": "ingestion", "description": "Kafka", "severity": "blocker"},
        ])

        summary = get_feedback_summary(db_path)
        assert summary["total"] == 3
        assert summary["by_severity"]["blocker"] == 2
        assert summary["by_severity"]["important"] == 1
        assert any(a["area"] == "catalog" and a["count"] == 2 for a in summary["top_areas"])


def test_get_dashboard_stats():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db(db_path)
        upsert_customer(db_path, "acme-corp", "Acme Corp")
        upsert_customer(db_path, "beta-inc", "Beta Inc")

        save_health_score(db_path, "acme-corp", 80)
        save_health_score(db_path, "beta-inc", 40)

        save_product_feedback(db_path, "acme-corp", [
            {"feature_area": "catalog", "description": "test", "severity": "blocker"},
        ])

        log_audit(db_path, "acme-corp", "approved", node_name="test_node")

        stats = get_dashboard_stats(db_path)
        assert stats["total_customers"] == 2
        assert stats["avg_health"] == 60  # (80 + 40) / 2
        assert stats["feedback_count"] == 1
        assert len(stats["recent_activity"]) == 1
        assert stats["recent_activity"][0]["customer_name"] == "Acme Corp"

