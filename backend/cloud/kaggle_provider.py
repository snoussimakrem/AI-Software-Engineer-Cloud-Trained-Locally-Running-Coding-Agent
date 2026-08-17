import subprocess
import json

from backend.cloud.provider import CloudProvider, SessionStatus, GPUInfo, ProviderQuota


class KaggleProvider(CloudProvider):
    """
    Kaggle implementation of CloudProvider.

    IMPORTANT — honesty about what's actually live vs. static:
    - Kaggle's public API has no endpoint for live GPU/VRAM stats or
      remaining weekly GPU-hour quota. Those figures below are the
      last publicly documented limits, NOT a live query. Verify current
      values at https://www.kaggle.com/docs/competitions#kernels-notebooks
      before relying on them for scheduling decisions.
    - There is no API to start a GPU session non-interactively — Kaggle
      requires either a kernel push (code-based, works for CPU/GPU batch
      jobs) or manually opening the notebook UI. We implement submit_job()
      via kernel push, which IS a real, legitimate API operation.
    - status() reflects whether we have a locally-registered CloudSession
      that's still healthy — not a live Kaggle-side session query, since
      no such endpoint exists.
    """

    name = "kaggle"

    async def gpu_info(self) -> GPUInfo:
        # Static, last-known info — Kaggle typically offers a T4 x2 or P100
        # depending on account tier/availability at kernel start time.
        # This is NOT a live query.
        return GPUInfo(name="T4/P100 (varies, not queryable live)", vram_gb=16.0)

    async def quota(self) -> ProviderQuota:
        # Last publicly documented limit as of this project's setup.
        # NOT fetched live — no API for this. Verify on kaggle.com/settings.
        return ProviderQuota(
            session_limit_hours=9.0,
            weekly_gpu_hours=30.0,
            notes="Static values — Kaggle has no live quota API. Verify at kaggle.com/settings.",
        )

    async def status(self) -> SessionStatus:
        # No live Kaggle-side query exists; real status comes from our
        # own SessionManager (Step 6), which health-checks the tunnel
        # endpoint directly. This method exists to satisfy the interface
        # but should not be relied on alone.
        return SessionStatus.MANUAL_ACTION_REQUIRED

    async def submit_job(self, job_config: dict) -> str:
        """
        Pushes a kernel to Kaggle via the real `kaggle kernels push` API.
        job_config must contain: {"kernel_dir": "<path to kernel folder
        with kernel-metadata.json>"}.
        This starts execution but does NOT give us a live tunnel URL —
        that must come from the notebook's own code (e.g. printing a
        cloudflared URL to its output), then registered manually via
        `ai-agent inference register`.
        """
        kernel_dir = job_config.get("kernel_dir")
        if not kernel_dir:
            return "NOT_SUPPORTED: job_config missing 'kernel_dir'"

        try:
            result = subprocess.run(
                ["kaggle", "kernels", "push", "-p", kernel_dir],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return f"FAILED: {result.stderr.strip()}"
            return result.stdout.strip()
        except FileNotFoundError:
            return "NOT_SUPPORTED: kaggle CLI not found"
        except subprocess.TimeoutExpired:
            return "FAILED: kaggle kernels push timed out"

    async def stop_job(self, job_id: str) -> bool:
        # Kaggle's API has no "stop kernel" endpoint — kernels run to
        # completion or timeout. This is a genuine platform limitation.
        return False
