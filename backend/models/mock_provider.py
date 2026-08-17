from backend.models.provider import ModelProvider, ChatMessage, GenerationResult
from typing import AsyncIterator


class MockModelProvider(ModelProvider):
    """Fake provider for testing the interface shape only — not a real model."""

    async def health(self) -> bool:
        return True

    async def generate(self, messages: list[ChatMessage]) -> GenerationResult:
        return GenerationResult(text="mock response", model="mock-model", tokens_used=3)

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        for chunk in ["mock ", "streamed ", "response"]:
            yield chunk

    async def list_models(self) -> list[str]:
        return ["mock-model"]
