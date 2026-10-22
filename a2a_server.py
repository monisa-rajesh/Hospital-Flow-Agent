
import uvicorn
from database import initialize_database, get_resources, get_patients

from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import TaskState
from starlette.applications import Starlette



class HospitalOperationsExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)

        if not context.current_task:
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )

        query = get_message_text(context.message).lower()
        initialize_database()

        if "bed" in query or "resource" in query:
            resources = get_resources()
            lines = ["Current simulated hospital resources:"]

            for item in resources:
                name = item.get("name", item.get("resource_type", "Resource"))
                available = item.get(
                    "available",
                    item.get("available_quantity", "unknown")
                )
                lines.append(f"{name}: {available} available")

            response = "\n".join(lines)

        elif "patient" in query or "queue" in query:
            patients = get_patients()
            response = (
                f"The patient queue contains {len(patients)} record(s)."
                if patients
                else "The patient queue is currently empty."
            )

        else:
            response = (
                "Please ask about hospital resources or the patient queue."
            )

        await updater.add_artifact(
            parts=[new_text_part(text=response, media_type="text/plain")]
        )

        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Operations response completed."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancellation is not supported in this demo.")


        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Reviewing the hospital operations request."),
        )

        query = get_message_text(context.message).lower()

        # Demo logic only; this does not make clinical decisions.
        if "bed" in query or "resource" in query:
            response = (
                "Hospital Operations Agent: The demo inventory has "
                "8 available beds, 4 doctors, 12 nurses, and 6 wheelchairs. "
                "Please verify current availability in the hospital dashboard."
            )
        elif "patient" in query or "queue" in query:
            response = (
                "Hospital Operations Agent: Check the patient queue in "
                "the Hospital Flow dashboard. Any prioritization must be "
                "verified by authorized clinical staff."
            )
        else:
            response = (
                "Hospital Operations Agent received your request: "
                f"{query}. Please specify whether you need a resource "
                "summary or a patient-queue summary."
            )

        await updater.add_artifact(
            parts=[new_text_part(text=response, media_type="text/plain")]
        )

        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Operations response completed."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancellation is not supported in this demo.")


agent_card = AgentCard(
    name="Hospital Operations Agent",
    description="Provides simulated hospital resource and patient-queue summaries.",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            url="http://127.0.0.1:9999/",
            protocol_version="1.0",
        )
    ],
    skills=[
        AgentSkill(
            id="hospital_operations",
            name="Hospital Operations Summary",
            description="Responds to simulated resource and patient-queue requests.",
            input_modes=["text/plain"],
            output_modes=["text/plain"],
            tags=["hospital", "operations", "resources"],
            examples=["Summarize available resources", "Summarize the patient queue"],
        )
    ],
)

handler = DefaultRequestHandler(
    agent_executor=HospitalOperationsExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

app = Starlette(
    routes=[
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(handler, "/", enable_v0_3_compat=True),
    ]
)

if __name__ == "__main__":
    print("Starting Hospital Operations A2A Agent at http://127.0.0.1:9999")
    uvicorn.run(app, host="127.0.0.1", port=9999)
