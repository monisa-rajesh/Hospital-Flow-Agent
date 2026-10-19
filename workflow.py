
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from database import get_resources


class HospitalState(TypedDict):
    patient_code: str
    age: int
    symptoms: str
    priority: str
    resource_summary: str
    final_report: str


def patient_intake(state: HospitalState):
    symptoms = state["symptoms"].lower()

    # Educational demonstration flags only.
    critical_words = [
        "not breathing",
        "unconscious",
        "severe bleeding",
    ]

    urgent_words = [
        "chest pain",
        "difficulty breathing",
        "fainting",
    ]

    if any(word in symptoms for word in critical_words):
        priority = "Critical flag"
    elif any(word in symptoms for word in urgent_words):
        priority = "Urgent flag"
    else:
        priority = "Routine review flag"

    return {"priority": priority}


def resource_monitor(state: HospitalState):
    resources = get_resources()

    summary = "; ".join(
        f"{item['name']}: {item['available']} available "
        f"out of {item['total']}"
        for item in resources
    )

    return {"resource_summary": summary}


def coordinator(state: HospitalState):
    report = (
        f"Patient ID: {state['patient_code']}\n"
        f"Age: {state['age']}\n"
        f"Demonstration flag: {state['priority']}\n"
        f"Resource summary: {state['resource_summary']}\n\n"
        "This is an educational workflow report. "
        "A qualified healthcare professional must make "
        "all clinical decisions."
    )

    return {"final_report": report}


builder = StateGraph(HospitalState)

builder.add_node("patient_intake", patient_intake)
builder.add_node("resource_monitor", resource_monitor)
builder.add_node("coordinator", coordinator)

builder.add_edge(START, "patient_intake")
builder.add_edge("patient_intake", "resource_monitor")
builder.add_edge("resource_monitor", "coordinator")
builder.add_edge("coordinator", END)

hospital_workflow = builder.compile()


def process_patient(patient_code, age, symptoms):
    return hospital_workflow.invoke({
        "patient_code": patient_code,
        "age": age,
        "symptoms": symptoms,
        "priority": "",
        "resource_summary": "",
        "final_report": "",
    })
