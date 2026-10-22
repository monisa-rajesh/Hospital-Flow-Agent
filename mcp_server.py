
from mcp.server.fastmcp import FastMCP

from database import (
    initialize_database,
    get_resources,
    get_patients,
)

mcp = FastMCP("HospitalFlowTools", json_response=True)


@mcp.tool()
def get_hospital_resources() -> list[dict]:
    """Return the simulated hospital resource inventory."""
    initialize_database()
    return get_resources()


@mcp.tool()
def get_patient_queue() -> list[dict]:
    """Return the simulated patient queue."""
    initialize_database()
    return get_patients()


if __name__ == "__main__":
    print("Starting Hospital Flow MCP server...")
    mcp.run(transport="streamable-http")
