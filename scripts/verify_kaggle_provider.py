import asyncio
from backend.cloud.kaggle_provider import KaggleProvider


async def main():
    provider = KaggleProvider()

    gpu = await provider.gpu_info()
    print(f"gpu_info() -> {gpu}  [static, not live]")

    quota = await provider.quota()
    print(f"quota() -> {quota}  [static, not live]")

    status = await provider.status()
    print(f"status() -> {status}")

    stop_result = await provider.stop_job("fake-job-id")
    print(f"stop_job() -> {stop_result}  [expected False — no API support]")


if __name__ == "__main__":
    asyncio.run(main())
