from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    UNHEALTHY = "UNHEALTHY"
    EXPIRING = "EXPIRING"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"


class GPUInfo(BaseModel):
    name: str | None = None
    vram_gb: float | None = None


class ProviderQuota(BaseModel):
    session_limit_hours: float | None = None
    weekly_gpu_hours: float | None = None
    notes: str | None = None


class CloudProvider(ABC):
    """
    Represents a free GPU platform (Kaggle, Colab, ...). Operations that
    can't be done through a legitimate API MUST return NOT_SUPPORTED /
    MANUAL_ACTION_REQUIRED rather than being faked.
    """

    name: str

    @abstractmethod
    async def gpu_info(self) -> GPUInfo:
        ...

    @abstractmethod
    async def quota(self) -> ProviderQuota:
        ...

    @abstractmethod
    async def status(self) -> SessionStatus:
        ...

    @abstractmethod
    async def submit_job(self, job_config: dict) -> str:
        """Returns NOT_SUPPORTED if the platform has no job-submission API."""

    @abstractmethod
    async def stop_job(self, job_id: str) -> bool:
        ...
