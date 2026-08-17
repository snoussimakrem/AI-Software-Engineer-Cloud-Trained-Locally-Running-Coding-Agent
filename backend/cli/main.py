import asyncio
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.core.config import settings
from backend.cloud.session_manager import SessionManager
from backend.cloud.health import check_endpoint_health

app = typer.Typer(help="AI Software Engineer - Control Center CLI")
inference_app = typer.Typer(help="Cloud inference session commands")
app.add_typer(inference_app, name="inference")

console = Console()


def _engine():
    return create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )


@app.command()
def status():
    """Overall system status: DB, config, active session."""
    asyncio.run(_status())


async def _status():
    console.print(f"[bold]model_provider[/bold]: {settings.model_provider}")
    console.print(f"[bold]app_env[/bold]: {settings.app_env}")

    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        session = await mgr.get_active_session()
        if session:
            console.print(f"[bold]active session[/bold]: {session.provider} ({session.status})")
        else:
            console.print("[bold]active session[/bold]: [yellow]none[/yellow]")
    await engine.dispose()


@inference_app.command("status")
def inference_status():
    """Detailed status of the current cloud inference session."""
    asyncio.run(_inference_status())


async def _inference_status():
    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        session = await mgr.get_active_session()

        if not session:
            console.print("[bold yellow]MANUAL_ACTION_REQUIRED[/bold yellow]")
            console.print("No active cloud inference session.")
            console.print("Open your prepared Kaggle/Colab notebook and start it, then run:")
            console.print("  ai-agent inference register <tunnel_url>")
            await engine.dispose()
            return

        healthy, latency, error = await check_endpoint_health(session.tunnel_url)

        table = Table(title="Cloud Inference Session")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Provider", session.provider)
        table.add_row("Model", session.model or "-")
        table.add_row("GPU", session.gpu or "-")
        table.add_row("Endpoint", session.tunnel_url)
        table.add_row("Status (recorded)", str(session.status))
        table.add_row("Live health", "[green]OK[/green]" if healthy else f"[red]FAIL: {error}[/red]")
        table.add_row("Latency", f"{latency:.3f}s" if latency else "-")
        table.add_row("Started", str(session.started_at))
        table.add_row("Expires", str(session.expires_at))
        console.print(table)

        if healthy:
            await mgr.mark_running(session.id)
        else:
            await mgr.mark_unhealthy(session.id)

    await engine.dispose()


@inference_app.command("register")
def inference_register(
    tunnel_url: str = typer.Argument(..., help="The HTTPS/HTTP tunnel URL from your cloud notebook"),
    provider: str = typer.Option("kaggle", help="kaggle | colab | other"),
    model: str = typer.Option(None, help="Model name being served"),
    gpu: str = typer.Option(None, help="GPU type, e.g. T4"),
):
    """Register a manually-started cloud inference session."""
    asyncio.run(_inference_register(tunnel_url, provider, model, gpu))


async def _inference_register(tunnel_url, provider, model, gpu):
    engine = _engine()
    async with AsyncSession(engine) as db:
        mgr = SessionManager(db)
        session = await mgr.register_manual_session(
            provider=provider, tunnel_url=tunnel_url, model=model, gpu=gpu
        )
        console.print(f"[green]Registered session {session.id}[/green] ({provider} -> {tunnel_url})")
    await engine.dispose()


if __name__ == "__main__":
    app()
