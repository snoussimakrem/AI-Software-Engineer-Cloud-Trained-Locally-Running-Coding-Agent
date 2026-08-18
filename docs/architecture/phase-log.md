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
- Step 8: README + architecture documentation.

## Phase 2 — Cloud inference, agent tools, dashboard

- Step 9: `KaggleProvider` — real `kaggle kernels push` implementation,
  real API verified (auth, `kernels list`, `kernels status`).
- Step 10: Real cloud inference verified end-to-end via Colab
  (llama.cpp server + cloudflared tunnel), answered a real coding
  prompt from this machine.
- Step 11: `CloudModelProvider` — real OpenAI-compatible HTTP client
  (generate/stream/health/list_models), verified live against the
  Colab endpoint.
- Steps 12-13: File tools (`list_files`, `read_file`, `search_code`,
  `write_file`, `edit_file`) scoped to a safe working directory with
  path-escape protection, verified in isolation.
- Step 14: Web dashboard (`backend/api/dashboard.py`,
  `backend/static/index.html`) — live session status, register/stop
  controls.
- `CodingAgent` (`backend/agents/coding_agent.py`) — JSON tool-calling
  loop built on the file tools. Known grounding bug found (agent
  read a file containing a function, then claimed it didn't exist);
  a revised system prompt with explicit grounding rules was written
  but is not yet committed — blocked on getting a live cloud endpoint
  to re-test against (see Phase 3 blockers).

## Phase 3 — Dataset pipeline and first training experiment

- Step 15: `HuggingFaceStorage` — real `CloudStorage` implementation
  against the Hugging Face Hub, full round-trip
  (upload/exists/list/checksum/download/delete) verified against a
  real private HF dataset repo.
- Model size decision: Qwen2.5-Coder-7B-Instruct chosen as the
  largest model with realistic QLoRA headroom on free-tier 16GB GPUs
  (Kaggle T4/P100, Colab T4) — 14B's published QLoRA minimum (~20-22GB)
  exceeds the hardware outright; 3B leaves capability on the table.
- Compliance check before generating any training data: Anthropic's
  Claude API is ruled out (Usage Policy prohibits training models on
  outputs). Poolside's free OpenRouter models have the identical
  restriction. Landed on two verified-permissive free teacher models
  via OpenRouter: `dots-studio/dots-3-note-preview:free` (Apache 2.0)
  and `nvidia/nemotron-3.5-lightning:free` (NVIDIA Open Model License).
- Step 16: Generated and versioned the `coding-v1` dataset — 38 real
  API calls across coding tasks, bug fixes, and agent-trajectory
  grounding reviews (deliberately including a case mirroring
  CodingAgent's own grounding bug), cleaned to 36 valid examples,
  split 32 train / 4 eval, uploaded via `HuggingFaceStorage`, recorded
  as a `DatasetVersion` row. $0 cost.
- Training notebook (`cloud/kaggle/train-coding-v1/`) built: QLoRA
  (4-bit NF4, LoRA r=16) on Qwen2.5-Coder-7B-Instruct, with
  checkpoint-upload-and-resume against the HF repo. Two real bugs
  caught via local CPU-only dry runs before touching a GPU: sequence
  length underestimated (raised to 2048 after measuring real token
  lengths), and the chat template's native assistant-token mask
  silently returns all zeros (replaced with a manually verified
  prefix-masking approach). Registered as `Experiment`
  `coding-v1-qwen7b-qlora` / `TrainingJob` (status `QUEUED`), not yet
  run.

## Known platform limitations hit (real, not bugs in our code)

- Kaggle has no API to stop a running kernel, and API-pushed "Save &
  Run All" batch commits appear to keep running independently of
  later pushes to the same kernel — pushing a new version does not
  stop an old one. Hit this directly: two earlier debugging pushes
  (an mlock-related multi-hour stall, then a failed CUDA build) both
  idled in an infinite tunnel-keepalive loop instead of exiting,
  which used up both of the account's 2 concurrent batch-GPU-session
  slots. Fixed going forward (the notebook now exits immediately if
  the server didn't start), but the already-running stuck sessions
  can only be waited out (bounded by Kaggle's 9-hour session cap).
- Kaggle has no API to set kernel Secrets — the training notebook's
  `HF_TOKEN` must be attached manually via the notebook editor's
  Add-ons -> Secrets menu before it can run.

## CodingAgent grounding fix — re-tested live, real result

Re-tested against a live Colab-hosted Qwen2.5-Coder-7B-Instruct
(q8_0 GGUF, real GPU inference verified via response latency ~1s).
Task: "Read calculator.py and tell me if the divide function has a
bug." The original bug — agent read the file (divide present in the
tool result), then claimed "there is no divide function," directly
contradicting its own tool result — is fixed. The agent this time
correctly references the divide function it actually read; no
hallucinated absence.

Not a clean pass, though: the agent concluded "the divide function
appears to be implemented correctly," which is questionable — `def
divide(a, b): return a / b` has no zero-division guard, a real latent
bug (the same pattern several coding-v1 bug_fix examples were built
around). This isn't a grounding failure (nothing contradicts the tool
result), but a separate code-review-thoroughness gap. It also made an
unnecessary extra tool call (`search_code('divide function')` -> `[]`)
after already having the answer, a minor violation of the "don't call
tools just to be sure" system prompt rule.

## Not yet done

- Push a Kaggle session slot free enough to actually run the training
  notebook (blocked on the session cap above) and attach the
  `HF_TOKEN` Kaggle Secret (manual, one-time) -- OR run the Colab
  variant (cloud/colab/train-coding-v1/) instead, now that inference
  has moved to Colab; same manual secret step applies there too.
- Deliberate kill-mid-training-and-resume test, to prove the
  checkpoint resilience guarantee for real.
- Address the code-review-thoroughness gap found above (agent didn't
  flag a real latent bug it wasn't explicitly asked to find) -- not
  blocking, but worth a future coding-v1 dataset addition targeting
  proactive bug-spotting, not just grounding.
- Base-model-vs-fine-tuned evaluation on real tasks, logged to the
  `Evaluation` table.
- Terminal sandboxing / test-fix loop for the coding agent (original
  Phase 6 scope, not started).
