import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path) -> None:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            phase TEXT NOT NULL DEFAULT 'discovery',
            health_score INTEGER,
            thread_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            action TEXT NOT NULL,
            node_name TEXT,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE IF NOT EXISTS health_score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            computed_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE IF NOT EXISTS product_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            feature_area TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'nice_to_have',
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """)
    conn.commit()
    conn.close()


def upsert_customer(db_path: Path, customer_id: str, customer_name: str, phase: str = "discovery") -> None:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO customers (customer_id, customer_name, phase, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(customer_id) DO UPDATE SET
               customer_name=excluded.customer_name,
               phase=excluded.phase,
               updated_at=excluded.updated_at""",
        (customer_id, customer_name, phase, now, now),
    )
    conn.commit()
    conn.close()


def list_customers(db_path: Path) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM customers ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_audit(db_path: Path, customer_id: str, action: str, node_name: str | None = None, details: str | None = None) -> None:
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO audit_log (customer_id, action, node_name, details, created_at) VALUES (?, ?, ?, ?, ?)",
        (customer_id, action, node_name, details, now),
    )
    conn.commit()
    conn.close()


# ── Health Score Persistence ──────────────────────────────────────────


def save_health_score(db_path: Path, customer_id: str, score: int) -> None:
    """Persist a health score snapshot and update the customer record."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO health_score_history (customer_id, score, computed_at) VALUES (?, ?, ?)",
        (customer_id, score, now),
    )
    conn.execute(
        "UPDATE customers SET health_score = ?, updated_at = ? WHERE customer_id = ?",
        (score, now, customer_id),
    )
    conn.commit()
    conn.close()


def get_health_score_history(db_path: Path, customer_id: str, limit: int = 20) -> list[dict]:
    """Return recent health score snapshots, oldest-first (for chart rendering)."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT score, computed_at FROM health_score_history WHERE customer_id = ? ORDER BY computed_at DESC LIMIT ?",
        (customer_id, limit),
    ).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


# ── Audit Log Retrieval ───────────────────────────────────────────────


def get_audit_log(db_path: Path, customer_id: str, limit: int = 50) -> list[dict]:
    """Return audit entries for a customer, most recent first."""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
        (customer_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Product Feedback CRUD ─────────────────────────────────────────────


def save_product_feedback(db_path: Path, customer_id: str, feedback_items: list[dict]) -> None:
    """Batch-insert product feedback items from graph state."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    for fb in feedback_items:
        conn.execute(
            "INSERT INTO product_feedback (customer_id, feature_area, description, severity, created_at) VALUES (?, ?, ?, ?, ?)",
            (customer_id, fb.get("feature_area", ""), fb.get("description", ""), fb.get("severity", "nice_to_have"), fb.get("created_at", now)),
        )
    conn.commit()
    conn.close()


def list_product_feedback(db_path: Path, customer_id: str | None = None) -> list[dict]:
    """List product feedback, optionally filtered by customer."""
    conn = get_connection(db_path)
    if customer_id:
        rows = conn.execute(
            "SELECT * FROM product_feedback WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM product_feedback ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_feedback_summary(db_path: Path) -> dict:
    """Aggregate feedback counts by severity and top feature areas."""
    conn = get_connection(db_path)
    severity_rows = conn.execute(
        "SELECT severity, COUNT(*) as cnt FROM product_feedback GROUP BY severity ORDER BY cnt DESC"
    ).fetchall()
    area_rows = conn.execute(
        "SELECT feature_area, COUNT(*) as cnt FROM product_feedback GROUP BY feature_area ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as cnt FROM product_feedback").fetchone()
    conn.close()
    return {
        "total": total["cnt"] if total else 0,
        "by_severity": {r["severity"]: r["cnt"] for r in severity_rows},
        "top_areas": [{"area": r["feature_area"], "count": r["cnt"]} for r in area_rows],
    }


# ── Dashboard Stats ──────────────────────────────────────────────────


def get_dashboard_stats(db_path: Path) -> dict:
    """Compute aggregate stats for the dashboard summary cards."""
    conn = get_connection(db_path)
    total = conn.execute("SELECT COUNT(*) as cnt FROM customers").fetchone()["cnt"]
    avg_health = conn.execute(
        "SELECT AVG(health_score) as avg FROM customers WHERE health_score IS NOT NULL"
    ).fetchone()["avg"]
    feedback_count = conn.execute("SELECT COUNT(*) as cnt FROM product_feedback").fetchone()["cnt"]
    recent_audit = conn.execute(
        "SELECT a.*, c.customer_name FROM audit_log a JOIN customers c ON a.customer_id = c.customer_id ORDER BY a.created_at DESC LIMIT 8"
    ).fetchall()
    conn.close()
    return {
        "total_customers": total,
        "avg_health": round(avg_health) if avg_health else None,
        "feedback_count": feedback_count,
        "recent_activity": [dict(r) for r in recent_audit],
    }
