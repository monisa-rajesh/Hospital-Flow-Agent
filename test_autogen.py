
import asyncio
from autogen_agents import run_operations_team


async def main():
    report = await run_operations_team()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
