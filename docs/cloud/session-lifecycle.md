# Cloud Inference Session Lifecycle

## States

CREATED -> STARTING -> RUNNING -> (UNHEALTHY | EXPIRING) -> STOPPED
                                        |
                                   EXPIRED / FAILED

## Flow

1. No session exists. `ai-agent inference status` reports
   `MANUAL_ACTION_REQUIRED` and instructs the user to start a cloud
   notebook manually.
2. User starts a Kaggle/Colab notebook, gets a tunnel URL.
3. `ai-agent inference register <url>` records a new `CloudSession` row
   in `STARTING` state.
4. `ai-agent inference status` performs a real HTTP health check against
   the endpoint and transitions the recorded status to `RUNNING` or
   `UNHEALTHY` based on the actual result — never assumed.
5. When the session ends (walltime limit, manual stop, or persistent
   health failures), it's marked `STOPPED`/`EXPIRED`/`FAILED`, and
   `get_active_session()` no longer returns it.

## Design constraint

The system never attempts to auto-start or auto-restart a cloud GPU
session — free platforms require a manual step, and pretending otherwise
would violate the free-only, ToS-respecting design goal.
