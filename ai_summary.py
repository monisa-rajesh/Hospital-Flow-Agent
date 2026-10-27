
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_cloud_model():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing.")

    model_name = os.getenv(
        "GOOGLE_MODEL",
        "gemini-3.5-flash-lite",
    )

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
    )


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

    prompt = f"""
You are an administrative assistant for a simulated hospital.

Resource availability:
{resources_text}

Total patients in the supplied data: {total_patients}
Patients currently waiting: {waiting_patients}

Patient data:
{patient_data}

Write a concise operations summary covering resource availability,
the waiting queue, and administrative observations.

Use only the supplied data. Do not invent information.
Do not diagnose patients or recommend treatment.
This is an educational simulation, not a clinical decision system.
"""

    try:
        response = get_cloud_model().invoke(prompt)
        return response.content

    except Exception as error:
        return (
            "Cloud AI operations summary is unavailable. "
            f"Please check the API key, model access, and quota. "
            f"Details: {error}"
        )
