
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from database import get_beds, assign_bed


class BedState(TypedDict, total=False):
    patient_code: str
    department: str
    bed_type: str
    recommended_bed: Optional[dict]
    recommendation_message: str
    used_fallback: bool
    approval: Any
    booking_status: str
    final_message: str


def find_bed(state: BedState):
    """Find a suitable bed without assigning it."""

    beds = get_beds()

    suitable_beds = [
        bed for bed in beds
        if bed["status"] == "Available"
        and bed["bed_type"] == state["bed_type"]
    ]

    # First try the requested department.
    department_beds = [
        bed for bed in suitable_beds
        if bed["department"] == state["department"]
    ]

    if department_beds:
        selected = department_beds[0]

        return {
            "recommended_bed": selected,
            "used_fallback": False,
            "recommendation_message": (
                f"Bed {selected['bed_code']} is available in "
                f"{selected['department']}."
            ),
            "booking_status": "awaiting_approval",
        }

    # Recovery: look for the same bed type in another department.
    alternatives = [
        bed for bed in suitable_beds
        if bed["department"] != state["department"]
    ]

    if alternatives:
        selected = alternatives[0]

        return {
            "recommended_bed": selected,
            "used_fallback": True,
            "recommendation_message": (
                f"No matching bed is available in "
                f"{state['department']}. Alternative found: "
                f"{selected['bed_code']} in {selected['department']}. "
                "Staff must review this alternative."
            ),
            "booking_status": "awaiting_approval",
        }

    return {
        "recommended_bed": None,
        "used_fallback": False,
        "recommendation_message": (
            "No available bed matches the requested bed type. "
            "No assignment was made. Staff must review the request."
        ),
        "booking_status": "no_bed_available",
        "final_message": (
            "Booking stopped: no matching bed is available."
        ),
    }


def route_after_search(state: BedState):
    if state.get("recommended_bed"):
        return "approval"
    return END


def request_human_approval(state: BedState):
    """Pause LangGraph until a person approves or rejects."""

    bed = state["recommended_bed"]

    decision = interrupt({
        "message": "Human approval is required before assignment.",
        "patient_code": state["patient_code"],
        "requested_department": state["department"],
        "recommended_bed": bed,
        "alternative_department": state.get("used_fallback", False),
        "recommendation": state["recommendation_message"],
    })

    approved = (
        isinstance(decision, dict)
        and decision.get("approved") is True
    )

    return {"approval": approved}


def route_after_approval(state: BedState):
    if state.get("approval") is True:
        return "assign"
    return "cancel"


def assign_recommended_bed(state: BedState):
    """Recheck availability, then attempt the assignment."""

    bed = state["recommended_bed"]
    bed_code = bed["bed_code"]

    # The bed might have been taken while approval was pending.
    current_bed = next(
        (
            item for item in get_beds()
            if item["bed_code"] == bed_code
        ),
        None,
    )

    if (
        current_bed is None
        or current_bed["status"] != "Available"
        or current_bed["bed_type"] != state["bed_type"]
        or (
            state.get("used_fallback") is False
            and current_bed["department"] != state["department"]
        )
    ):
        # Recovery: search again rather than assigning a stale choice.
        return {
            "booking_status": "retry_required",
            "final_message": (
                "The recommended bed is no longer available or "
                "no longer matches the request. Refresh and run "
                "the allocation workflow again."
            ),
        }

    try:
        assign_bed(state["patient_code"], bed_code)
    except (ValueError, RuntimeError) as error:
        return {
            "booking_status": "assignment_failed",
            "final_message": (
                f"Assignment failed safely: {error}. "
                "Refresh the bed list and try again."
            ),
        }

    # Verify the database actually records the assignment.
    updated_beds = get_beds()
    assigned = next(
        (
            item for item in updated_beds
            if item["bed_code"] == bed_code
        ),
        None,
    )

    if (
        assigned
        and assigned["status"] == "Occupied"
        and assigned.get("patient_code") == state["patient_code"]
    ):
        return {
            "booking_status": "assigned",
            "final_message": (
                f"Verified: bed {bed_code} in "
                f"{assigned['department']} has been assigned "
                f"to patient {state['patient_code']}."
            ),
        }

    return {
        "booking_status": "verification_failed",
        "final_message": (
            "The assignment could not be verified. Check the "
            "bed inventory before attempting another assignment."
        ),
    }


def cancel_booking(state: BedState):
    return {
        "booking_status": "rejected",
        "final_message": (
            "Staff rejected the recommendation. No bed was assigned."
        ),
    }


builder = StateGraph(BedState)

builder.add_node("find_bed", find_bed)
builder.add_node("approval", request_human_approval)
builder.add_node("assign", assign_recommended_bed)
builder.add_node("cancel", cancel_booking)

builder.add_edge(START, "find_bed")
builder.add_conditional_edges(
    "find_bed",
    route_after_search,
    {
        "approval": "approval",
        END: END,
    },
)
builder.add_conditional_edges(
    "approval",
    route_after_approval,
    {
        "assign": "assign",
        "cancel": "cancel",
    },
)
builder.add_edge("assign", END)
builder.add_edge("cancel", END)

# In-memory checkpointing supports pause/resume while this app process runs.
bed_workflow = builder.compile(checkpointer=MemorySaver())
