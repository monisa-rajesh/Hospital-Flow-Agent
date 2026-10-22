
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

from database import get_resources, get_patients


# Replace this with the exact tag shown by `ollama list`.
OLLAMA_MODEL = "qwen3:4b"  # Example: "qwen3:4b"

OLLAMA_BASE_URL = "http://localhost:11434/v1"


def create_local_model_client():
    return OpenAIChatCompletionClient(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )


async def run_operations_team():
    resources = get_resources()
    patients = get_patients()

    resource_text = "\n".join(
        f"{r['name']}: {r['available']} available "
        f"out of {r['total']}"
        for r in resources
    )

    waiting_count = sum(
        p["status"] == "Waiting"
        for p in patients
    )

    client = create_local_model_client()

    analyst = AssistantAgent(
        name="ResourceAnalyst",
        model_client=client,
        system_message=(
            "You are a resource inventory analyst for a student "
            "hospital simulation. Report only facts supported by "
            "the supplied counts. Do not diagnose or recommend "
            "medical treatment."
        ),
    )

    coordinator = AssistantAgent(
        name="OperationsCoordinator",
        model_client=client,
        system_message=(
            "Prepare a concise administrative summary from the "
            "analyst's findings. Do not invent numbers or make "
            "clinical decisions. State that the data is simulated."
        ),
    )

    team = RoundRobinGroupChat(
        [analyst, coordinator],
        termination_condition=MaxMessageTermination(2),
    )

    task = (
        "Analyze this simulated hospital inventory:\n"
        f"{resource_text}\n\n"
        f"Waiting demonstration records: {waiting_count}\n\n"
        "The Resource Analyst should describe the inventory. "
        "The Operations Coordinator should summarize the findings."
    )

    try:
        result = await team.run(task=task)

        return "\n\n".join(
            f"{message.source}:\n{message.content}"
            for message in result.messages
            if isinstance(message.content, str)
        )
    finally:
        await client.close()
