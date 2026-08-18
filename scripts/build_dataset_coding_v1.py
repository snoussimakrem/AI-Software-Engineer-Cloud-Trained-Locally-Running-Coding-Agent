import asyncio
import hashlib
import json
import os
import random

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession

from backend.core.config import settings
from backend.db.models import DatasetVersion
from backend.storage.hf_storage import HuggingFaceStorage
from scripts.generate_teacher_dataset import CODING_SYSTEM, BUGFIX_SYSTEM, TRAJECTORY_SYSTEM

RAW_PATH = "datasets/raw/coding-v1-raw.jsonl"
OUT_DIR = "datasets/processed/coding-v1"
HF_REPO_ID = "makremlupin/ai-software-engineer-artifacts"
DATASET_NAME = "coding-v1"
EVAL_FRACTION = 0.1
MIN_EVAL = 3
SEED = 42

SYSTEM_BY_CATEGORY = {
    "coding_task": CODING_SYSTEM,
    "bug_fix": BUGFIX_SYSTEM,
    "trajectory_review": TRAJECTORY_SYSTEM,
}

REFUSAL_MARKERS = ["i cannot", "i can't", "i'm sorry", "as an ai"]


def load_raw() -> list[dict]:
    with open(RAW_PATH) as f:
        return [json.loads(line) for line in f]


def is_valid(record: dict) -> bool:
    response = record.get("response")
    if not response or len(response.strip()) < 20:
        return False
    lowered = response.lower()
    if any(marker in lowered for marker in REFUSAL_MARKERS):
        return False
    return True


def to_chat_example(record: dict) -> dict:
    system = SYSTEM_BY_CATEGORY[record["category"]]
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": record["prompt"]},
            {"role": "assistant", "content": record["response"].strip()},
        ],
        "task_id": record["task_id"],
        "category": record["category"],
        "source_model": record["model"],
    }


def dedupe(examples: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for ex in examples:
        key = hashlib.sha256(ex["messages"][-1]["content"].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            deduped.append(ex)
    return deduped


def split_train_eval(examples: list[dict]) -> tuple[list[dict], list[dict]]:
    rng = random.Random(SEED)
    shuffled = examples[:]
    rng.shuffle(shuffled)
    n_eval = max(MIN_EVAL, round(len(shuffled) * EVAL_FRACTION))
    return shuffled[n_eval:], shuffled[:n_eval]


def write_jsonl(path: str, examples: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def dataset_hash(examples: list[dict]) -> str:
    h = hashlib.sha256()
    for ex in sorted(examples, key=lambda e: e["task_id"] + e["source_model"]):
        h.update(json.dumps(ex, sort_keys=True).encode())
    return h.hexdigest()


async def main():
    raw = load_raw()
    print(f"loaded {len(raw)} raw records")

    valid = [r for r in raw if is_valid(r)]
    print(f"{len(valid)}/{len(raw)} passed validation")

    examples = [to_chat_example(r) for r in valid]
    examples = dedupe(examples)
    print(f"{len(examples)} after dedupe")

    train, eval_ = split_train_eval(examples)
    print(f"split -> train={len(train)} eval={len(eval_)}")

    train_path = f"{OUT_DIR}/train.jsonl"
    eval_path = f"{OUT_DIR}/eval.jsonl"
    write_jsonl(train_path, train)
    write_jsonl(eval_path, eval_)

    storage = HuggingFaceStorage(repo_id=HF_REPO_ID)
    train_meta = await storage.upload(train_path, f"datasets/{DATASET_NAME}/train.jsonl")
    eval_meta = await storage.upload(eval_path, f"datasets/{DATASET_NAME}/eval.jsonl")
    print(f"uploaded train -> {train_meta.location}")
    print(f"uploaded eval -> {eval_meta.location}")

    full_hash = dataset_hash(train + eval_)

    engine: AsyncEngine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with AsyncSession(engine) as session:
        version = DatasetVersion(
            name=DATASET_NAME,
            dataset_hash=full_hash,
            num_examples=len(train) + len(eval_),
            source="openrouter:dots-studio/dots-3-note-preview:free+nvidia/nemotron-3.5-lightning:free",
            cloud_uri=f"{HF_REPO_ID}/datasets/{DATASET_NAME}/",
        )
        session.add(version)
        await session.commit()
        await session.refresh(version)
        print(f"DatasetVersion recorded -> id={version.id} name={version.name} num_examples={version.num_examples}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
