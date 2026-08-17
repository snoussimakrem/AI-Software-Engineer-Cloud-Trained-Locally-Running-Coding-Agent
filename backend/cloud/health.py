import httpx


async def check_endpoint_health(base_url: str, timeout: float = 5.0) -> tuple[bool, float | None, str | None]:
    """
    Pings a cloud inference endpoint's /health (or root) and reports
    (is_healthy, latency_seconds, error_message).
    """
    import time

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/health")
        latency = time.monotonic() - start
        if resp.status_code == 200:
            return True, latency, None
        return False, latency, f"status {resp.status_code}"
    except Exception as e:
        latency = time.monotonic() - start
        return False, latency, str(e)
