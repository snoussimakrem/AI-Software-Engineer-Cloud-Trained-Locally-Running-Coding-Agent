import asyncio
import os
import tempfile

from backend.storage.hf_storage import HuggingFaceStorage

REPO_ID = "makremlupin/ai-software-engineer-artifacts"


async def main():
    storage = HuggingFaceStorage(repo_id=REPO_ID)

    with tempfile.TemporaryDirectory() as tmp:
        local_src = os.path.join(tmp, "verify_upload.txt")
        with open(local_src, "w") as f:
            f.write("hf_storage real round-trip test\n")

        remote_path = "verify/verify_upload.txt"

        meta = await storage.upload(local_src, remote_path)
        print(f"upload() -> {meta}")

        exists = await storage.exists(remote_path)
        print(f"exists() -> {exists}")

        listing = await storage.list("verify/")
        print(f"list('verify/') -> {listing}")

        checksum = await storage.checksum(remote_path)
        print(f"checksum() -> {checksum}")

        local_dst = os.path.join(tmp, "verify_download.txt")
        downloaded_path = await storage.download(remote_path, local_dst)
        with open(downloaded_path) as f:
            content = f.read()
        print(f"download() -> {downloaded_path} | content: {content.strip()!r}")

        deleted = await storage.delete(remote_path)
        print(f"delete() -> {deleted}")

        exists_after_delete = await storage.exists(remote_path)
        print(f"exists() after delete -> {exists_after_delete}")


if __name__ == "__main__":
    asyncio.run(main())
