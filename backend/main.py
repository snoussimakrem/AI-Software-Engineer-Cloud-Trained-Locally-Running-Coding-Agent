from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.core.config import settings

app = FastAPI(title="AI Software Engineer - Control Center")

engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))


@app.get("/health")
async def health():
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "database": db_status,
        "model_provider": settings.model_provider,
        "app_env": settings.app_env,
    }
