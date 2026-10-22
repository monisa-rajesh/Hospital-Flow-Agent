
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8000/mcp"
    ) as (read_stream, write_stream, _):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print("-", tool.name)

            resources = await session.call_tool(
                "get_hospital_resources",
                arguments={},
            )
            print("\nResource inventory:")
            print(resources)

            patients = await session.call_tool(
                "get_patient_queue",
                arguments={},
            )
            print("\nPatient queue:")
            print(patients)


if __name__ == "__main__":
    asyncio.run(main())
