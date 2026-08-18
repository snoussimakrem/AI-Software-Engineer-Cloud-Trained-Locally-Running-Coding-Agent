import os
import shutil
import tempfile

from huggingface_hub import HfApi
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError

from backend.storage.provider import CloudStorage, ArtifactMetadata


class HuggingFaceStorage(CloudStorage):
    """
    Real implementation of CloudStorage backed by a Hugging Face Hub repo.
    Auth token is picked up automatically from ~/.cache/huggingface/token
    (or HF_TOKEN env var) via HfApi's default resolution — never passed
    or stored in code.
    """

    def __init__(self, repo_id: str, repo_type: str = "dataset"):
        self.repo_id = repo_id
        self.repo_type = repo_type
        self.api = HfApi()

    async def upload(self, local_path: str, remote_path: str) -> ArtifactMetadata:
        self.api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=remote_path,
            repo_id=self.repo_id,
            repo_type=self.repo_type,
        )
        size = os.path.getsize(local_path)
        checksum = await self.checksum(remote_path)
        return ArtifactMetadata(
            artifact_id=f"{self.repo_id}:{remote_path}",
            artifact_type="dataset",
            size_bytes=size,
            checksum=checksum,
            provider="huggingface",
            location=f"{self.repo_id}/{remote_path}",
        )

    async def download(self, remote_path: str, local_path: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            cached_path = self.api.hf_hub_download(
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                filename=remote_path,
                local_dir=tmp,
            )
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            shutil.copy(cached_path, local_path)
        return local_path

    async def exists(self, remote_path: str) -> bool:
        return self.api.file_exists(
            repo_id=self.repo_id,
            filename=remote_path,
            repo_type=self.repo_type,
        )

    async def list(self, prefix: str = "") -> list[str]:
        try:
            files = self.api.list_repo_files(repo_id=self.repo_id, repo_type=self.repo_type)
        except RepositoryNotFoundError:
            return []
        return [f for f in files if f.startswith(prefix)]

    async def delete(self, remote_path: str) -> bool:
        try:
            self.api.delete_file(
                path_in_repo=remote_path,
                repo_id=self.repo_id,
                repo_type=self.repo_type,
            )
            return True
        except EntryNotFoundError:
            return False

    async def checksum(self, remote_path: str) -> str:
        info = self.api.repo_info(repo_id=self.repo_id, repo_type=self.repo_type, files_metadata=True)
        for sibling in info.siblings:
            if sibling.rfilename == remote_path:
                if sibling.lfs:
                    return sibling.lfs.get("sha256", sibling.blob_id)
                return sibling.blob_id
        raise FileNotFoundError(f"{remote_path} not found in {self.repo_id}")
