from backend.storage.provider import CloudStorage, ArtifactMetadata


class MockCloudStorage(CloudStorage):
    """Fake storage for testing the interface shape only — no real upload/download."""

    def __init__(self):
        self._fake_files: dict[str, bytes] = {}

    async def upload(self, local_path: str, remote_path: str) -> ArtifactMetadata:
        self._fake_files[remote_path] = b"fake-bytes"
        return ArtifactMetadata(
            artifact_id="mock-artifact-1",
            artifact_type="dataset",
            size_bytes=len(self._fake_files[remote_path]),
            checksum="mockchecksum123",
            provider="mock",
            location=remote_path,
            version="v1",
        )

    async def download(self, remote_path: str, local_path: str) -> str:
        return local_path

    async def exists(self, remote_path: str) -> bool:
        return remote_path in self._fake_files

    async def list(self, prefix: str = "") -> list[str]:
        return [k for k in self._fake_files if k.startswith(prefix)]

    async def delete(self, remote_path: str) -> bool:
        return self._fake_files.pop(remote_path, None) is not None

    async def checksum(self, remote_path: str) -> str:
        return "mockchecksum123"
