import asyncio
from backend.storage.mock_storage import MockCloudStorage
from backend.cloud.mock_provider import MockCloudProvider


async def main():
    storage = MockCloudStorage()

    meta = await storage.upload("local/fake.txt", "datasets/v1/fake.txt")
    print(f"upload() -> {meta}")

    exists = await storage.exists("datasets/v1/fake.txt")
    print(f"exists() -> {exists}")

    listing = await storage.list("datasets/")
    print(f"list() -> {listing}")

    checksum = await storage.checksum("datasets/v1/fake.txt")
    print(f"checksum() -> {checksum}")

    deleted = await storage.delete("datasets/v1/fake.txt")
    print(f"delete() -> {deleted}")

    print()
    cloud = MockCloudProvider()

    gpu = await cloud.gpu_info()
    print(f"gpu_info() -> {gpu}")

    quota = await cloud.quota()
    print(f"quota() -> {quota}")

    status = await cloud.status()
    print(f"status() -> {status}")

    job_result = await cloud.submit_job({})
    print(f"submit_job() -> {job_result}")


if __name__ == "__main__":
    asyncio.run(main())
