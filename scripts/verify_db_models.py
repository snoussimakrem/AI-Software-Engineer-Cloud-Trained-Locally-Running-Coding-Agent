import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.core.config import settings
from backend.db.models import Experiment


async def main():
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )

    async with AsyncSession(engine) as session:
        exp = Experiment(
            name="phase1-smoke-test",
            description="Proving the ORM writes and reads correctly",
        )
        session.add(exp)
        await session.commit()
        await session.refresh(exp)
        print(f"Inserted -> id={exp.id} name={exp.name} created_at={exp.created_at}")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Experiment).where(Experiment.name == "phase1-smoke-test")
        )
        found = result.scalar_one()
        print(f"Read back -> id={found.id} name={found.name} description={found.description}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
