from backend.cloud.provider import CloudProvider, SessionStatus, GPUInfo, ProviderQuota


class MockCloudProvider(CloudProvider):
    """Fake GPU platform for testing the interface shape only."""

    name = "mock-provider"

    async def gpu_info(self) -> GPUInfo:
        return GPUInfo(name="Mock T4", vram_gb=16.0)

    async def quota(self) -> ProviderQuota:
        return ProviderQuota(session_limit_hours=9.0, weekly_gpu_hours=30.0, notes="mock quota")

    async def status(self) -> SessionStatus:
        return SessionStatus.RUNNING

    async def submit_job(self, job_config: dict) -> str:
        return "NOT_SUPPORTED"

    async def stop_job(self, job_id: str) -> bool:
        return True
