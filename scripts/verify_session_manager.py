import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.core.config import settings
from backend.cloud.session_manager import SessionManager
from backend.cloud.health import check_endpoint_health


async def main():
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )

    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)

        existing = await mgr.get_active_session()
        print(f"get_active_session() before registering -> {existing}")

        session = await mgr.register_manual_session(
            provider="mock-local",
            tunnel_url="http://localhost:8080",
            model="mock-model",
            gpu="none (local test)",
        )
        print(f"registered -> id={session.id} status={session.status} tunnel_url={session.tunnel_url}")

        healthy, latency, error = await check_endpoint_health(session.tunnel_url)
        print(f"check_endpoint_health() -> healthy={healthy} latency={latency:.3f}s error={error}")

        if healthy:
            await mgr.mark_running(session.id)
        else:
            await mgr.mark_unhealthy(session.id)

        active = await mgr.get_active_session()
        print(f"get_active_session() after -> id={active.id} status={active.status}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
