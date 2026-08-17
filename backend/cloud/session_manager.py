from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CloudSession
from backend.cloud.provider import SessionStatus


class SessionManager:
    """
    Tracks the lifecycle of the (at most one, for now) active cloud
    inference session. Does NOT start cloud notebooks itself — free
    platforms require a manual step (Section 20 of the spec). This
    manager only records and reports state.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_session(self) -> CloudSession | None:
        """Returns the most recent session that isn't STOPPED/EXPIRED/FAILED."""
        result = await self.db.execute(
            select(CloudSession)
            .where(
                CloudSession.status.notin_(
                    [SessionStatus.STOPPED, SessionStatus.EXPIRED, SessionStatus.FAILED]
                )
            )
            .order_by(CloudSession.started_at.desc())
        )
        return result.scalars().first()

    async def register_manual_session(
        self,
        provider: str,
        tunnel_url: str,
        model: str | None = None,
        gpu: str | None = None,
        expires_in_hours: float = 9.0,
    ) -> CloudSession:
        """
        Called AFTER you've manually started a Kaggle/Colab notebook and
        have a real tunnel URL. This is the ai-agent inference register
        step from Section 20 of the spec.
        """
        now = datetime.now(timezone.utc)
        session = CloudSession(
            provider=provider,
            status=SessionStatus.STARTING,
            gpu=gpu,
            model=model,
            tunnel_url=tunnel_url,
            started_at=now,
            last_heartbeat=now,
            expires_at=now + timedelta(hours=expires_in_hours),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def mark_running(self, session_id: str) -> None:
        await self._update_status(session_id, SessionStatus.RUNNING)

    async def mark_unhealthy(self, session_id: str) -> None:
        await self._update_status(session_id, SessionStatus.UNHEALTHY)

    async def stop_session(self, session_id: str) -> None:
        await self._update_status(session_id, SessionStatus.STOPPED)

    async def heartbeat(self, session_id: str) -> None:
        session = await self.db.get(CloudSession, session_id)
        if session:
            session.last_heartbeat = datetime.now(timezone.utc)
            await self.db.commit()

    async def _update_status(self, session_id: str, status: SessionStatus) -> None:
        session = await self.db.get(CloudSession, session_id)
        if session:
            session.status = status
            await self.db.commit()
