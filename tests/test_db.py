import tempfile
from pathlib import Path

from src.db.app_db import init_db, list_customers, log_audit, upsert_customer


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
