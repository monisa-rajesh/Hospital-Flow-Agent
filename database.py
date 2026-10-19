
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hospital.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL,
                symptoms TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                name TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                available INTEGER NOT NULL
            )
        """)

        defaults = [
            ("Beds", 20, 8),
            ("Doctors", 10, 4),
            ("Nurses", 20, 12),
            ("Wheelchairs", 10, 6),
        ]

        for name, total, available in defaults:
            conn.execute("""
                INSERT OR IGNORE INTO resources
                (name, total, available)
                VALUES (?, ?, ?)
            """, (name, total, available))


def add_patient(patient_code, age, symptoms, priority):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO patients
            (patient_code, age, symptoms, priority)
            VALUES (?, ?, ?, ?)
        """, (patient_code, age, symptoms, priority))


def get_patients():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM patients
            ORDER BY
                CASE priority
                    WHEN 'Critical flag' THEN 0
                    WHEN 'Urgent flag' THEN 1
                    ELSE 2
                END,
                created_at ASC,
                id ASC
        """).fetchall()

        return [dict(row) for row in rows]


def get_resources():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM resources ORDER BY name
        """).fetchall()

        return [dict(row) for row in rows]


def update_resource(name, total, available):
    if total < 0 or available < 0 or available > total:
        raise ValueError(
            "Available units must be between zero and total units."
        )

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO resources (name, total, available)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                total = excluded.total,
                available = excluded.available
        """, (name, total, available))


def update_patient_status(patient_code, status):
    allowed = ["Waiting", "Under Review", "Completed"]

    if status not in allowed:
        raise ValueError("Invalid demonstration status.")

    with get_connection() as conn:
        conn.execute("""
            UPDATE patients SET status = ?
            WHERE patient_code = ?
        """, (status, patient_code))


def delete_patient(patient_code):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM patients WHERE patient_code = ?
        """, (patient_code,))
