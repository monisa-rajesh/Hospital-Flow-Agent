import asyncio
import json
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from typing import TypedDict
import uuid

import httpx
from langgraph.graph import StateGraph, START, END
from database import get_resources


A2A_SERVER_URL = "http://127.0.0.1:9999/"


class HospitalState(TypedDict):
    patient_code: str
    age: int
    symptoms: str
    priority: str
    resource_summary: str
    a2a_summary: str
    mcp_summary: str
    final_report: str
    ai_summary: str


def patient_intake(state: HospitalState):
    symptoms = state["symptoms"].lower()

    # Educational demonstration flags only.
    critical_words = [
        "not breathing",
        "unconscious",
        "severe bleeding",
    ]
    high_priority_keywords = [
        "accident",
        "road accident",
        "vehicle accident",
        "injury",
        "injured",
        "fracture",
        "heavy bleeding",
    ]


    urgent_words = [
        "chest pain",
        "difficulty breathing",
        "fainting",
    ]

    if any(word in symptoms for word in critical_words):
        priority = "Critical flag"
    elif any(word in symptoms for word in high_priority_keywords):
        priority = "High priority flag"
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


def a2a_operations_agent(state: HospitalState):
    """Request an operations summary from the local A2A agent."""

    query = "Summarize available hospital resources"

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": query,
                    }
                ],
            }
        },
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(A2A_SERVER_URL, json=payload)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            summary = f"A2A agent returned an error: {result['error']}"
        else:
            task = result.get("result", {})
            status = task.get("status", {}).get("state", "")

            if status != "completed":
                summary = (
                    f"A2A task did not complete successfully. "
                    f"Status: {status or 'unknown'}"
                )
            else:
                messages = []

                for artifact in task.get("artifacts", []):
                    for part in artifact.get("parts", []):
                        if part.get("kind") == "text":
                            messages.append(part.get("text", ""))

                summary = "\n".join(messages) or (
                    "A2A task completed without a text artifact."
                )

    except (httpx.HTTPError, ValueError) as error:
        summary = (
            "A2A agent is unavailable. "
            f"Local resource monitoring is still available. Details: {error}"
        )

    return {"a2a_summary": summary}

MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"


async def fetch_mcp_data():
    async with streamable_http_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            resources = await session.call_tool(
                "get_hospital_resources",
                arguments={},
            )

            patients = await session.call_tool(
                "get_patient_queue",
                arguments={},
            )

            return {
                "resources": resources,
                "patients": patients,
            }


def mcp_monitor(state: HospitalState):
    """Retrieve hospital resources and patient queue through MCP."""

    try:
        data = asyncio.run(fetch_mcp_data())

        def extract_result(result):
            structured = getattr(result, "structuredContent", None)

            if structured is not None:
                return structured

            text_parts = [
                item.text
                for item in getattr(result, "content", [])
                if hasattr(item, "text")
            ]

            return text_parts if text_parts else str(result)

        resource_data = extract_result(data["resources"])
        patient_data = extract_result(data["patients"])

        summary = (
            "MCP resource inventory:\n"
            + json.dumps(resource_data, indent=2, default=str)
            + "\n\nMCP patient queue:\n"
            + json.dumps(patient_data, indent=2, default=str)
        )

    except Exception as error:
        summary = f"MCP connection failed: {error}"

    return {"mcp_summary": summary}



def ollama_summary(state: HospitalState):
    """Generate a friendly administrative summary using Gemini."""

    prompt = f"""
You are a friendly hospital operations assistant.

Write a short, clear administrative update in natural English.
Avoid technical language and unnecessary repetition.

Patient ID: {state['patient_code']}
Patient age: {state['age']}
Educational priority flag: {state['priority']}
Resource availability: {state['resource_summary']}
MCP response: {state['mcp_summary']}
A2A response: {state['a2a_summary']}

Use these headings:

### Patient Overview
Briefly describe the recorded patient details and educational flag.

### Patient Queue
Summarize queue information only if it is present in the MCP response.
Do not invent information.

### Available Resources
List the available beds, doctors, nurses, and wheelchairs using
the supplied resource information.

### System Status
Clearly state whether MCP and A2A are available or unavailable,
based on the supplied responses.

### Important Notes
Mention only relevant missing information.

Keep the response under 180 words.
Use readable Markdown.
Do not return JSON, Python dictionaries, metadata, or signatures.
Do not diagnose patients, recommend treatment, or make clinical
triage decisions. This is an educational simulation.
"""

    try:
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

        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            max_retries=2,
        )

        response = model.invoke(prompt)
        summary = response.content

        # Extract readable text if Gemini returns content blocks.
        if isinstance(summary, list):
            text_parts = []

            for block in summary:
                if isinstance(block, dict):
                    text_value = block.get("text", "")
                    if text_value:
                        text_parts.append(str(text_value))
                elif isinstance(block, str):
                    text_parts.append(block)
                else:
                    text_value = getattr(block, "text", "")
                    if text_value:
                        text_parts.append(str(text_value))

            summary = "\n".join(text_parts)

        if not isinstance(summary, str):
            summary = str(summary)

        return {"ai_summary": summary}

    except Exception as error:
        return {
            "ai_summary": (
                "Gemini AI summary is unavailable. "
                "Check the API key, model access, and quota. "
                f"Details: {error}"
            )
        }





def coordinator(state: HospitalState):
    report = (
        f"Patient ID: {state['patient_code']}\n"
        f"Age: {state['age']}\n"
        f"Demonstration flag: {state['priority']}\n"
        f"Resource summary: {state['resource_summary']}\n"
        f"A2A Operations Agent: {state['a2a_summary']}\n\n"
        f"MCP data:\n{state['mcp_summary']}\n\n"
        f"AI Operations Summary:\n{state['ai_summary']}\n\n"
        "This is an educational workflow report. "
        "Symptom flags are not diagnoses or clinical triage decisions. "
        "A qualified healthcare professional must make all clinical decisions."
    )

    return {"final_report": report}


builder = StateGraph(HospitalState)

builder.add_node("patient_intake", patient_intake)
builder.add_node("resource_monitor", resource_monitor)
builder.add_node("a2a_operations_agent", a2a_operations_agent)
builder.add_node("coordinator", coordinator)
builder.add_node("mcp_monitor", mcp_monitor)
builder.add_node("ollama_summary", ollama_summary)

builder.add_edge(START, "patient_intake")
builder.add_edge("patient_intake", "resource_monitor")
builder.add_edge("resource_monitor", "mcp_monitor")
builder.add_edge("mcp_monitor", "a2a_operations_agent")
builder.add_edge("a2a_operations_agent", "ollama_summary")
builder.add_edge("ollama_summary", "coordinator")
builder.add_edge("coordinator", END)

hospital_workflow = builder.compile()


def process_patient(patient_code, age, symptoms):
    return hospital_workflow.invoke({
        "patient_code": patient_code,
        "age": age,
        "symptoms": symptoms,
        "priority": "",
        "resource_summary": "",
        "a2a_summary": "",
        "final_report": "",
        "mcp_summary": "",
        "ai_summary": "",
    })
