from abc import ABC, abstractmethod
from pydantic import BaseModel


class ArtifactMetadata(BaseModel):
    artifact_id: str
    artifact_type: str  # "dataset" | "checkpoint" | "adapter" | "model" | "eval"
    size_bytes: int | None = None
    checksum: str | None = None
    provider: str
    location: str  # e.g. HF repo id, or path within it
    version: str | None = None


class CloudStorage(ABC):
    """
    Contract for any artifact storage backend (Hugging Face Hub first,
    others later). Large files always live here — never locally,
    never in Git.
    """

    @abstractmethod
    async def upload(self, local_path: str, remote_path: str) -> ArtifactMetadata:
        ...

    @abstractmethod
    async def download(self, remote_path: str, local_path: str) -> str:
        ...

    @abstractmethod
    async def exists(self, remote_path: str) -> bool:
        ...

    @abstractmethod
    async def list(self, prefix: str = "") -> list[str]:
        ...

    @abstractmethod
    async def delete(self, remote_path: str) -> bool:
        ...

    @abstractmethod
    async def checksum(self, remote_path: str) -> str:
        ...
