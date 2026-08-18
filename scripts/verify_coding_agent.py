import asyncio
import sys

from backend.models.cloud_provider import CloudModelProvider
from backend.agents.tools.file_tools import FileTools
from backend.agents.coding_agent import CodingAgent


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.verify_coding_agent <cloud_base_url>")
        sys.exit(1)

    base_url = sys.argv[1]
    model = CloudModelProvider(base_url=base_url)
    tools = FileTools(root="/home/msi/agent-test-repo")
    agent = CodingAgent(model=model, tools=tools, max_iterations=6)

    steps = await agent.run(
        "Read calculator.py and tell me if the divide function has a bug. "
        "Just report findings, don't fix anything yet."
    )

    for step in steps:
        print(step)


if __name__ == "__main__":
    asyncio.run(main())
