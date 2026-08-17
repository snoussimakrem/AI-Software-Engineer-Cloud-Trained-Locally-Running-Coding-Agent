# AI Software Engineer — Cloud-Trained, Locally-Running Coding Agent

A control-center architecture where the local machine handles orchestration,
monitoring, and storage management, while all LLM inference and training
VRAM usage happens on free cloud GPU platforms (Kaggle/Colab).

## Hard requirement

The local machine (control center) does **not** perform LLM inference or
training locally. All GPU/VRAM work happens in the cloud. See
`docs/architecture/overview.md` for the full reasoning.

## Status

Phase 1 (Foundation) — in progress. See `docs/architecture/phase-log.md`
for what's built and verified so far.

## Requirements

- Python 3.12 (managed via `uv`, isolated from system Python)
- Docker (for local PostgreSQL)
- `uv` (https://astral.sh/uv)

## Setup

```bash
cp .env.example .env   # edit with real local values
uv sync
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload --port 8080
```

## CLI

```bash
uv run ai-agent status
uv run ai-agent inference status
uv run ai-agent inference register <tunnel_url> --provider kaggle --model <name>
```

## Project layout

- `backend/` — the actual Python application (API, CLI, DB models, cloud abstractions)
- `cloud/`, `datasets/`, `training/`, `models/`, `infrastructure/` — non-code project folders (configs, notebooks, docs, artifacts — not Python packages)
- `docs/` — architecture and lifecycle documentation

## Documentation

- `docs/architecture/overview.md` — system design and reasoning
- `docs/cloud/session-lifecycle.md` — cloud inference session state machine
- `docs/architecture/phase-log.md` — what's been built and verified, phase by phase
