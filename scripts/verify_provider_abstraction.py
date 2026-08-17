import asyncio
from backend.models.mock_provider import MockModelProvider
from backend.models.provider import ChatMessage


async def main():
    provider = MockModelProvider()

    healthy = await provider.health()
    print(f"health() -> {healthy}")

    models = await provider.list_models()
    print(f"list_models() -> {models}")

    result = await provider.generate([ChatMessage(role="user", content="hi")])
    print(f"generate() -> {result}")

    print("stream() -> ", end="")
    async for chunk in provider.stream([ChatMessage(role="user", content="hi")]):
        print(chunk, end="")
    print()


if __name__ == "__main__":
    asyncio.run(main())
