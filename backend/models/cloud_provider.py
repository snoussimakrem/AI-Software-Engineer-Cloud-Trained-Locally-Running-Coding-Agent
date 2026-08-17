import json
import httpx
from typing import AsyncIterator

from backend.models.provider import ModelProvider, ChatMessage, GenerationResult


class CloudModelProvider(ModelProvider):
    """
    Real implementation of ModelProvider, talking to any OpenAI-compatible
    server (llama.cpp server, vLLM, Ollama, etc.) over HTTP. The agent
    only ever sees this interface — swapping providers later means
    changing the base_url/model, not rewriting agent code.
    """

    def __init__(self, base_url: str, model: str | None = None, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/v1/models")
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]

    async def generate(self, messages: list[ChatMessage]) -> GenerationResult:
        payload = {
            "messages": [m.model_dump() for m in messages],
            "max_tokens": 512,
        }
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return GenerationResult(
            text=choice,
            model=data.get("model", self.model or "unknown"),
            tokens_used=usage.get("total_tokens"),
        )

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        payload = {
            "messages": [m.model_dump() for m in messages],
            "max_tokens": 512,
            "stream": True,
        }
        if self.model:
            payload["model"] = self.model

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[len("data: "):]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
