# Phase / Step Log

## Phase 1 — Foundation

- Step 1-2: Git repo, project structure, Python 3.12 venv (uv),
  PostgreSQL via Docker (port 5434, data on secondary partition).
- Step 3: FastAPI skeleton, `/health` verified against live DB.
- Step 4: `ModelProvider`, `CloudStorage`, `CloudProvider` interfaces
  defined and verified with mock implementations.
- Step 5: SQLAlchemy models for the registry (Experiment, DatasetVersion,
  TrainingJob, ModelVersion, Evaluation, CloudSession, Artifact),
  Alembic migrations, ORM read/write verified against live Postgres.
- Step 6: `SessionManager` + real HTTP health checker, full lifecycle
  verified (register -> health check -> status transition).
- Step 7: `ai-agent` CLI (status, inference status, inference register),
  installed as a real entry point via `uv`/setuptools packaging.
- Step 8: README + architecture documentation (this step).

## Not yet done

- Real cloud provider implementations (Kaggle/Colab) — currently only
  interfaces + mocks exist.
- Dataset pipeline, training job execution, checkpoint upload/resume.
- Autonomous coding agent (tools, terminal sandboxing, test/fix loop).
