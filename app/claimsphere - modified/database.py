"""
database.py
-----------
PostgreSQL database layer for ClaimSphere AI.

This file replaces all direct SQL calls in the app and agents.
Everything talks through these helper functions.
"""

import psycopg2
from psycopg2.extras import RealDictCursor


# ====================================================
# DATABASE CONFIG (same as your Streamlit app)
# ====================================================
DB_CONFIG = {
    "host": "localhost",
    "port": "5433",
    "dbname": "claims_DB",
    "user": "postgres",
    "password": "Envy@2025"
}


# ====================================================
# CONNECTION
# ====================================================
def get_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )


# ====================================================
# INIT DB (safe check)
# ====================================================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id SERIAL PRIMARY KEY,
            policy_number TEXT,
            customer_name TEXT,
            claim_date TEXT,
            claim_amount FLOAT,
            photo_path TEXT,
            status TEXT
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ====================================================
# GET HISTORY (Agent 1 uses this)
# ====================================================
def get_claim_history(policy_number: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM claims
        WHERE policy_number = %s
        ORDER BY claim_date DESC
    """, (policy_number,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


# ====================================================
# INSERT CLAIM (final step)
# ====================================================
def insert_claim(
    policy_number: str,
    customer_name: str,
    claim_date: str,
    claim_amount: float,
    photo_path: str,
    status: str
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO claims (
            policy_number,
            customer_name,
            claim_date,
            claim_amount,
            photo_path,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        policy_number,
        customer_name,
        claim_date,
        claim_amount,
        photo_path,
        status
    ))

    conn.commit()
    cursor.close()
    conn.close()


# ====================================================
# SEED DATA (optional testing)
# ====================================================
'''
def seed_sample_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM claims")
    count = cursor.fetchone()[0]

    if count > 0:
        cursor.close()
        conn.close()
        return

    sample_claims = [
        ("POL-1001", "Jane Doe", "2025-11-02", 1800.00, "data/photos/POL-1001", "approved"),
        ("POL-1001", "Jane Doe", "2026-01-15", 2200.00, "data/photos/POL-1001", "approved"),
        ("POL-2002", "Mark Allen", "2025-06-20", 9500.00, "data/photos/POL-2002", "flagged_fraud"),
        ("POL-3003", "Priya Nair", "2026-03-10", 950.00, "data/photos/POL-3003", "approved"),
    ]

    cursor.executemany("""
        INSERT INTO claims (
            policy_number,
            customer_name,
            claim_date,
            claim_amount,
            photo_path,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, sample_claims)

    conn.commit()
    cursor.close()
    conn.close()
    '''