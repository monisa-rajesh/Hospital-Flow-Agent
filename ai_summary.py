
from langchain_ollama import ChatOllama


def generate_operations_summary(resource_data, patient_data):
    resources_text = "\n".join(
        f"- {r['name']}: {r['available']} available "
        f"out of {r['total']}"
        for r in resource_data
    )

    total_patients = len(patient_data)
    waiting_patients = sum(
        p["status"] == "Waiting"
        for p in patient_data
    )

    # Replace this with a model name from `ollama list`.
    model = ChatOllama(
        model="qwen3:4b",
        temperature=0
    )

    prompt = f"""
    You are an operations assistant for an educational
    hospital management simulation.

    Resource inventory:
    {resources_text}

    Total simulated patients: {total_patients}
    Waiting patients: {waiting_patients}

    Write a short administrative report describing
    resource availability and inventory figures that
    may need review.

    Do not diagnose patients, recommend treatment,
    or make clinical decisions. Do not invent data.
    Clearly state that this is a simulation.
    """

    response = model.invoke(prompt)
    return response.content
