"""
database.py
-----------
This file handles ALL database work for the project.

We use SQLite (not PostgreSQL) on purpose:
- SQLite is just a single file on your disk (claims.db) - no server to install,
  no Docker, no username/password to configure.
- It is perfect for a learning project or a small demo with one user.
- If you later want multiple people using this at once over the internet,
  you would switch to PostgreSQL - but the SQL queries below would barely change.

The ONE table we need:

    claims
    ------
    id              -> auto-incrementing row number
    policy_number   -> e.g. "POL-1001" (this is how we look up a customer)
    customer_name   -> e.g. "Jane Doe"
    claim_date      -> when the accident happened
    claim_amount    -> how much was paid out for that claim
    photo_path      -> where we saved that claim's photos on disk
    status          -> "approved", "rejected", "flagged_fraud"

That's it. One table answers every question Agent 1 needs:
"has this person claimed before, how much, when, any past fraud flags."
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "claims.db"


def get_connection():
    """Open a connection to the SQLite database file."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row["claim_amount"]
    return conn


def init_db():
    """
    Create the claims table if it doesn't already exist.
    Safe to call every time the app starts - it won't wipe existing data.
    """
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            claim_date    TEXT NOT NULL,
            claim_amount  REAL NOT NULL,
            photo_path    TEXT,
            status        TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_claim_history(policy_number: str) -> list[dict]:
    """
    Agent 1 calls this function. Given a policy number, return every
    past claim tied to it, most recent first.

    This is literally what "the agent talks to the database" means -
    it's just a SQL SELECT, wrapped in a Python function.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT claim_date, claim_amount, status, photo_path
        FROM claims
        WHERE policy_number = ?
        ORDER BY claim_date DESC
        """,
        (policy_number,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_claim(
    policy_number: str,
    customer_name: str,
    claim_date: str,
    claim_amount: float,
    photo_path: str,
    status: str,
) -> int:
    """
    Save a finished claim to the database so future claims from the
    same policy number can be checked against it. Returns the new row id.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO claims (policy_number, customer_name, claim_date, claim_amount, photo_path, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (policy_number, customer_name, claim_date, claim_amount, photo_path, status),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def seed_sample_data():
    """
    Insert a few fake past claims so you have something to test against
    immediately, without manually typing data into the database.
    Only inserts if the table is currently empty.
    """
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    conn.close()

    if count > 0:
        return  # already has data, don't duplicate

    sample_claims = [
        ("POL-1001", "Jane Doe", "2025-11-02", 1800.00, "data/photos/POL-1001", "approved"),
        ("POL-1001", "Jane Doe", "2026-01-15", 2200.00, "data/photos/POL-1001", "approved"),
        ("POL-2002", "Mark Allen", "2025-06-20", 9500.00, "data/photos/POL-2002", "flagged_fraud"),
        ("POL-3003", "Priya Nair", "2026-03-10", 950.00, "data/photos/POL-3003", "approved"),
    ]
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO claims (policy_number, customer_name, claim_date, claim_amount, photo_path, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        sample_claims,
    )
    conn.commit()
    conn.close()
