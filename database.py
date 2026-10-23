
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "hospital.db"

# Departments available in the educational prototype.
DEFAULT_DEPARTMENTS = [
    ("General Medicine", "Routine medical consultations"),
    ("Cardiology", "Heart-related consultations"),
    ("Orthopedics", "Bone and joint consultations"),
    ("Neurology", "Nervous system consultations"),
    ("Emergency", "Requests requiring staff review"),
]

BED_TYPES = ["General", "Private", "ICU"]

PATIENT_STATUSES = [
    "Waiting",
    "Under Review",
    "Completed",
    "Transferred",
    "Discharged",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create tables and safely add new prototype features."""

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
                total INTEGER NOT NULL CHECK(total >= 0),
                available INTEGER NOT NULL
                    CHECK(available >= 0 AND available <= total)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS beds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bed_code TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                bed_type TEXT NOT NULL DEFAULT 'General',
                status TEXT NOT NULL DEFAULT 'Available'
                    CHECK(status IN ('Available', 'Occupied', 'Maintenance')),
                patient_code TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL,
                from_department TEXT,
                to_department TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Requested'
                    CHECK(status IN (
                        'Requested', 'Approved', 'Completed', 'Cancelled'
                    )),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS discharges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL,
                reason TEXT NOT NULL,
                discharged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'Info'
                    CHECK(severity IN ('Info', 'Warning', 'Critical')),
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        for name, description in DEFAULT_DEPARTMENTS:
            conn.execute("""
                INSERT OR IGNORE INTO departments (name, description)
                VALUES (?, ?)
            """, (name, description))

        # Seed individual bed records only when the bed table is empty.
        existing_beds = conn.execute(
            "SELECT COUNT(*) FROM beds"
        ).fetchone()[0]

        if existing_beds == 0:
            bed_resource = conn.execute("""
                SELECT total, available
                FROM resources
                WHERE name = 'Beds'
            """).fetchone()

            if bed_resource:
                total = bed_resource["total"]
                available = bed_resource["available"]

                for number in range(1, total + 1):
                    bed_status = (
                        "Available" if number <= available else "Occupied"
                    )
                    department = (
                        "General Medicine"
                        if number <= total // 2
                        else "Emergency"
                    )

                    conn.execute("""
                        INSERT INTO beds
                        (bed_code, department, bed_type, status)
                        VALUES (?, ?, 'General', ?)
                    """, (
                        f"BED-{number:03d}",
                        department,
                        bed_status,
                    ))


# ---------------- PATIENTS ----------------

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


def update_patient_status(patient_code, status):
    if status not in PATIENT_STATUSES:
        raise ValueError("Invalid patient status.")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE patients
            SET status = ?
            WHERE patient_code = ?
        """, (status, patient_code))

        if cursor.rowcount == 0:
            raise ValueError("Patient not found.")


def delete_patient(patient_code):
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM patients WHERE patient_code = ?
        """, (patient_code,))


# ---------------- RESOURCES ----------------

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

    # Individual bed records are managed by bed functions.
    if name == "Beds":
        raise ValueError(
            "Update individual beds through Bed Management so counts "
            "remain consistent."
        )

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO resources (name, total, available)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                total = excluded.total,
                available = excluded.available
        """, (name, total, available))


def _sync_bed_resource(conn):
    """Keep the Beds resource count aligned with individual bed records."""

    counts = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) AS available
        FROM beds
    """).fetchone()

    conn.execute("""
        INSERT INTO resources (name, total, available)
        VALUES ('Beds', ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            total = excluded.total,
            available = excluded.available
    """, (counts["total"], counts["available"] or 0))


# ---------------- DEPARTMENTS / ROUTING ----------------

def get_departments():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM departments
            WHERE active = 1
            ORDER BY name
        """).fetchall()

        return [dict(row) for row in rows]


def add_department(name, description):
    if not name.strip():
        raise ValueError("Department name is required.")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO departments (name, description)
            VALUES (?, ?)
        """, (name.strip(), description.strip()))


def recommend_department(symptoms):
    """
    Demonstration keyword routing only.
    This is not a clinical assessment or diagnosis.
    """
    text = symptoms.lower()

    rules = [
        (["heart", "chest", "cardiac"], "Cardiology"),
        (["bone", "joint", "fracture"], "Orthopedics"),
        (["nerve", "seizure", "headache"], "Neurology"),
        (["emergency", "urgent"], "Emergency"),
    ]

    for keywords, department in rules:
        if any(word in text for word in keywords):
            return {
                "department": department,
                "reason": "Matched a demonstration keyword rule.",
                "requires_staff_review": True,
            }

    return {
        "department": "General Medicine",
        "reason": "Default department suggestion.",
        "requires_staff_review": True,
    }


# ---------------- BEDS / ALLOCATION ----------------

def get_beds():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM beds ORDER BY bed_code
        """).fetchall()

        return [dict(row) for row in rows]


def recommend_bed(department=None, bed_type="General"):
    """Recommend a bed without assigning it."""

    with get_connection() as conn:
        if department:
            row = conn.execute("""
                SELECT * FROM beds
                WHERE status = 'Available'
                  AND department = ?
                  AND bed_type = ?
                ORDER BY bed_code
                LIMIT 1
            """, (department, bed_type)).fetchone()
        else:
            row = conn.execute("""
                SELECT * FROM beds
                WHERE status = 'Available'
                  AND bed_type = ?
                ORDER BY bed_code
                LIMIT 1
            """, (bed_type,)).fetchone()

        return dict(row) if row else None


def assign_bed(patient_code, bed_code):
    """Assign a bed only when explicitly requested by the operator."""

    with get_connection() as conn:
        patient = conn.execute("""
            SELECT status FROM patients WHERE patient_code = ?
        """, (patient_code,)).fetchone()

        if not patient:
            raise ValueError("Patient not found.")

        if patient["status"] in ("Completed", "Transferred", "Discharged"):
            raise ValueError("Cannot assign a bed to a closed patient record.")

        bed = conn.execute("""
            SELECT status FROM beds WHERE bed_code = ?
        """, (bed_code,)).fetchone()

        if not bed or bed["status"] != "Available":
            raise ValueError("Bed is not available.")

        cursor = conn.execute("""
            UPDATE beds
            SET status = 'Occupied',
                patient_code = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE bed_code = ? AND status = 'Available'
        """, (patient_code, bed_code))

        if cursor.rowcount != 1:
            raise ValueError("Bed assignment failed; refresh and retry.")

        conn.execute("""
            UPDATE patients SET status = 'Under Review'
            WHERE patient_code = ?
        """, (patient_code,))

        _sync_bed_resource(conn)


def release_patient_bed(patient_code):
    """Release all beds associated with a patient."""

    with get_connection() as conn:
        conn.execute("""
            UPDATE beds
            SET status = 'Available',
                patient_code = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE patient_code = ?
        """, (patient_code,))

        _sync_bed_resource(conn)


# ---------------- DISCHARGE ----------------

def discharge_patient(patient_code, reason):
    """Record a confirmed discharge and release assigned beds."""

    with get_connection() as conn:
        patient = conn.execute("""
            SELECT status FROM patients WHERE patient_code = ?
        """, (patient_code,)).fetchone()

        if not patient:
            raise ValueError("Patient not found.")

        if patient["status"] in ("Discharged", "Transferred", "Completed"):
            raise ValueError("Patient record is already closed.")

        conn.execute("""
            INSERT INTO discharges (patient_code, reason)
            VALUES (?, ?)
        """, (patient_code, reason.strip() or "No reason supplied"))

        conn.execute("""
            UPDATE patients SET status = 'Discharged'
            WHERE patient_code = ?
        """, (patient_code,))

        conn.execute("""
            UPDATE beds
            SET status = 'Available',
                patient_code = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE patient_code = ?
        """, (patient_code,))

        _sync_bed_resource(conn)

        conn.execute("""
            INSERT INTO notifications (category, message, severity)
            VALUES ('Discharge', ?, 'Info')
        """, (f"Patient {patient_code} was recorded as discharged.",))


def get_discharges():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM discharges ORDER BY discharged_at DESC
        """).fetchall()

        return [dict(row) for row in rows]


# ---------------- TRANSFERS ----------------

def request_transfer(patient_code, to_department, reason):
    with get_connection() as conn:
        patient = conn.execute("""
            SELECT status FROM patients WHERE patient_code = ?
        """, (patient_code,)).fetchone()

        if not patient:
            raise ValueError("Patient not found.")

        if patient["status"] in ("Discharged", "Transferred", "Completed"):
            raise ValueError("Cannot transfer a closed patient record.")

        department = conn.execute("""
            SELECT name FROM departments
            WHERE name = ? AND active = 1
        """, (to_department,)).fetchone()

        if not department:
            raise ValueError("Select an active department.")

        current_bed = conn.execute("""
            SELECT department FROM beds
            WHERE patient_code = ?
            LIMIT 1
        """, (patient_code,)).fetchone()

        from_department = (
            current_bed["department"] if current_bed else None
        )

        cursor = conn.execute("""
            INSERT INTO transfers
            (patient_code, from_department, to_department, reason)
            VALUES (?, ?, ?, ?)
        """, (
            patient_code,
            from_department,
            to_department,
            reason.strip(),
        ))

        conn.execute("""
            INSERT INTO notifications (category, message, severity)
            VALUES ('Transfer', ?, 'Info')
        """, (
            f"Transfer request #{cursor.lastrowid} for {patient_code} "
            f"to {to_department} requires staff review.",
        ))

        return cursor.lastrowid


def get_transfers():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM transfers ORDER BY created_at DESC, id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_transfer_status(transfer_id, status):
    allowed = ["Requested", "Approved", "Completed", "Cancelled"]

    if status not in allowed:
        raise ValueError("Invalid transfer status.")

    with get_connection() as conn:
        transfer = conn.execute("""
            SELECT * FROM transfers WHERE id = ?
        """, (transfer_id,)).fetchone()

        if not transfer:
            raise ValueError("Transfer request not found.")

        old_status = transfer["status"]

        if old_status in ("Completed", "Cancelled"):
            raise ValueError("This transfer request is already closed.")

        if status == "Completed" and old_status != "Approved":
            raise ValueError("A transfer must be approved before completion.")

        if status == "Completed":
            conn.execute("""
                UPDATE beds
                SET status = 'Available',
                    patient_code = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE patient_code = ?
            """, (transfer["patient_code"],))

            conn.execute("""
                UPDATE patients SET status = 'Transferred'
                WHERE patient_code = ?
            """, (transfer["patient_code"],))

            _sync_bed_resource(conn)

        conn.execute("""
            UPDATE transfers
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, transfer_id))

        conn.execute("""
            INSERT INTO notifications (category, message, severity)
            VALUES ('Transfer', ?, 'Info')
        """, (
            f"Transfer request #{transfer_id} status changed to {status}.",
        ))


# ---------------- NOTIFICATIONS ----------------

def add_notification(category, message, severity="Info"):
    if severity not in ("Info", "Warning", "Critical"):
        raise ValueError("Invalid notification severity.")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO notifications (category, message, severity)
            VALUES (?, ?, ?)
        """, (category, message, severity))


def get_notifications(unread_only=False):
    with get_connection() as conn:
        if unread_only:
            rows = conn.execute("""
                SELECT * FROM notifications
                WHERE is_read = 0
                ORDER BY created_at DESC, id DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM notifications
                ORDER BY created_at DESC, id DESC
            """).fetchall()

        return [dict(row) for row in rows]


def mark_notification_read(notification_id):
    with get_connection() as conn:
        conn.execute("""
            UPDATE notifications SET is_read = 1
            WHERE id = ?
        """, (notification_id,))


def refresh_resource_alerts(low_availability_ratio=0.20):
    """Create alerts for resources at or below the configured threshold."""

    created = []

    for resource in get_resources():
        total = resource["total"]
        available = resource["available"]

        if total > 0 and available / total <= low_availability_ratio:
            message = (
                f"Low availability: {resource['name']} has "
                f"{available} of {total} units available."
            )
            add_notification("Resource", message, "Warning")
            created.append(message)

    return created
