# Architecture Overview

## Core principle

The local PC is a **control center only**: orchestration, monitoring,
storage metadata, database, CLI, API. It never runs LLM inference or
training itself — all VRAM-bound work happens on free cloud GPU platforms.

## Why this split

Free GPU platforms (Kaggle, Colab) are designed for batch/session-based
compute, not always-on services: sessions have walltime limits, require
manual start, and can terminate at any time. The local PC's job is to
survive those interruptions gracefully — tracking state, resuming
training from checkpoints, and reconnecting to a new inference session
when the old one dies.

## Components

- **backend/models/** — `ModelProvider` interface: abstracts whatever LLM
  server is currently running in the cloud (Ollama, vLLM, llama.cpp,
  Transformers+FastAPI). The agent only talks to this interface.
- **backend/storage/** — `CloudStorage` interface: abstracts artifact
  storage (Hugging Face Hub first). Large files never live locally or
  in Git.
- **backend/cloud/** — `CloudProvider` interface + `SessionManager`:
  represents a GPU platform and tracks the lifecycle of the current
  inference session.
- **backend/db/** — SQLAlchemy models + Alembic migrations: the local
  registry of experiments, training jobs, model versions, evaluations,
  cloud sessions, and artifacts. Metadata lives here; large files live
  in the cloud.
- **backend/cli/** — `ai-agent` command-line tool wrapping the above.

## No fake automation

If a cloud platform requires manual action (opening a notebook, clicking
Run), the system represents that explicitly as `MANUAL_ACTION_REQUIRED`
rather than pretending it's automated.
