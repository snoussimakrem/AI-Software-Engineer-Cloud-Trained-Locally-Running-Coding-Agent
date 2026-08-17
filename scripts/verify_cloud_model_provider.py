import asyncio
import sys
from backend.models.cloud_provider import CloudModelProvider
from backend.models.provider import ChatMessage


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.verify_cloud_model_provider <base_url>")
        sys.exit(1)

    base_url = sys.argv[1]
    provider = CloudModelProvider(base_url=base_url)

    healthy = await provider.health()
    print(f"health() -> {healthy}")

    models = await provider.list_models()
    print(f"list_models() -> {models}")

    result = await provider.generate([
        ChatMessage(role="user", content="In one sentence, what does a for loop do?")
    ])
    print(f"generate() -> {result.text[:200]}")
    print(f"tokens_used -> {result.tokens_used}")

    print("stream() -> ", end="", flush=True)
    async for chunk in provider.stream([
        ChatMessage(role="user", content="Count from 1 to 5.")
    ]):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
