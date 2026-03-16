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
