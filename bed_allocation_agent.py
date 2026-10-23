
from database import (
    get_beds,
    recommend_bed,
    assign_bed,
)


def recommend_bed_for_patient(
    patient_code,
    department=None,
    bed_type="General",
):
    """
    Recommend an available bed for a demo patient.
    This function does not assign the bed.
    """

    available_beds = [
        bed for bed in get_beds()
        if bed["status"] == "Available"
    ]

    if not available_beds:
        return {
            "success": False,
            "message": "No beds are currently available.",
            "recommendation": None,
        }

    bed = recommend_bed(
        department=department,
        bed_type=bed_type,
    )

    if bed is None:
        return {
            "success": False,
            "message": (
                "No available bed matches the selected "
                "department and bed type."
            ),
            "recommendation": None,
        }

    return {
        "success": True,
        "message": (
            f"Bed {bed['bed_code']} is available in "
            f"{bed['department']}."
        ),
        "recommendation": {
            "patient_code": patient_code,
            "bed_code": bed["bed_code"],
            "department": bed["department"],
            "bed_type": bed["bed_type"],
        },
    }


def confirm_bed_assignment(patient_code, bed_code):
    """
    Assign a recommended bed after explicit operator confirmation.
    """

    assign_bed(patient_code, bed_code)

    return {
        "success": True,
        "message": (
            f"Bed {bed_code} has been assigned to "
            f"demo patient {patient_code}."
        ),
    }
