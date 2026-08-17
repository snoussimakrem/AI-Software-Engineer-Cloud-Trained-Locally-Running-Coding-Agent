from fastapi import APIRouter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.core.config import settings
from backend.cloud.session_manager import SessionManager
from backend.cloud.health import check_endpoint_health

router = APIRouter(prefix="/api", tags=["dashboard"])


def _engine():
    return create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )


@router.get("/status")
async def system_status():
    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        session = await mgr.get_active_session()

        result = {
            "app_env": settings.app_env,
            "model_provider": settings.model_provider,
            "session": None,
        }

        if session:
            healthy, latency, error = await check_endpoint_health(session.tunnel_url)
            result["session"] = {
                "id": session.id,
                "provider": session.provider,
                "model": session.model,
                "gpu": session.gpu,
                "tunnel_url": session.tunnel_url,
                "status": str(session.status),
                "healthy": healthy,
                "latency": latency,
                "error": error,
                "started_at": str(session.started_at),
                "expires_at": str(session.expires_at),
            }
            if healthy:
                await mgr.mark_running(session.id)
            else:
                await mgr.mark_unhealthy(session.id)

    await engine.dispose()
    return result


@router.post("/session/register")
async def register_session(tunnel_url: str, provider: str = "colab", model: str | None = None, gpu: str | None = None):
    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        session = await mgr.register_manual_session(
            provider=provider, tunnel_url=tunnel_url, model=model, gpu=gpu
        )
    await engine.dispose()
    return {"id": session.id, "status": str(session.status)}


@router.post("/session/stop")
async def stop_session(session_id: str):
    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        await mgr.stop_session(session_id)
    await engine.dispose()
    return {"stopped": session_id}
