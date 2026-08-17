from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class GenerationResult(BaseModel):
    text: str
    model: str
    tokens_used: int | None = None


class ModelProvider(ABC):
    """
    Contract every model backend must satisfy — cloud notebook running
    Ollama/vLLM/llama.cpp/Transformers, doesn't matter which. The agent
    only ever talks to this interface, never to a specific backend.
    """

    @abstractmethod
    async def health(self) -> bool:
        """Return True if the model server is reachable and ready."""

    @abstractmethod
    async def generate(self, messages: list[ChatMessage]) -> GenerationResult:
        """Non-streaming completion."""

    @abstractmethod
    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Streaming completion, yields text chunks."""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Models currently available on the remote server."""
