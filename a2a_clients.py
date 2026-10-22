
import asyncio
import uuid
import httpx

SERVER_URL = "http://127.0.0.1:9999/"


async def main():
    message = input(
        "Enter a request (example: Summarize available resources): "
    ).strip()

    if not message:
        print("Please enter a request.")
        return

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
                        "text": message,
                    }
                ],
            }
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        card_response = await client.get(
            SERVER_URL + ".well-known/agent-card.json"
        )
        card_response.raise_for_status()
        card = card_response.json()
        print(f"\nConnected to: {card.get('name', 'A2A agent')}")

        response = await client.post(SERVER_URL, json=payload)
        response.raise_for_status()
        result = response.json()

    if "error" in result:
        print("\nA2A error:")
        print(result["error"])
        return

    task = result.get("result", {})
    print("\nA2A server response:")
    print("Task status:", task.get("status", {}).get("state", "unknown"))

    for artifact in task.get("artifacts", []):
        for part in artifact.get("parts", []):
            if part.get("kind") == "text":
                print(part.get("text", ""))

    if not task.get("artifacts"):
        print(task)


if __name__ == "__main__":
    asyncio.run(main())
