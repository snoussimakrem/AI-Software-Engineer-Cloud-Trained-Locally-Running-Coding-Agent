import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.core.config import settings
from backend.db.models import Experiment, TrainingJob, ModelVersion, Evaluation
from backend.storage.hf_storage import HuggingFaceStorage

HF_REPO_ID = "makremlupin/ai-software-engineer-artifacts"
JOB_NAME = "coding-v1-qwen7b-qlora"
BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"


async def main():
    storage = HuggingFaceStorage(repo_id=HF_REPO_ID)
    local_path = f"/tmp/{JOB_NAME}-results.json"
    await storage.download(f"evaluations/{JOB_NAME}/results.json", local_path)
    with open(local_path) as f:
        results = json.load(f)
    print(f"loaded results: {results}")

    engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))
    async with AsyncSession(engine) as session:
        result = await session.execute(select(Experiment).where(Experiment.name == JOB_NAME))
        experiment = result.scalar_one()
        result = await session.execute(
            select(TrainingJob).where(TrainingJob.experiment_id == experiment.id)
        )
        job = result.scalar_one()

        job.status = "COMPLETED"
        job.metrics = results

        base_version = ModelVersion(
            model_type="base",
            base_model=BASE_MODEL,
            provider="huggingface",
            cloud_uri=BASE_MODEL,
            status="baseline",
        )
        finetuned_version = ModelVersion(
            training_job_id=job.id,
            model_type="qlora",
            base_model=BASE_MODEL,
            provider="huggingface",
            cloud_uri=f"{HF_REPO_ID}/adapters/{JOB_NAME}",
            status="candidate",
        )
        session.add_all([base_version, finetuned_version])
        await session.flush()

        base_eval = Evaluation(
            model_version_id=base_version.id,
            score=results["base_eval_loss"],
            metrics={"eval_loss": results["base_eval_loss"], "perplexity": results["base_perplexity"]},
        )
        finetuned_eval = Evaluation(
            model_version_id=finetuned_version.id,
            score=results["finetuned_eval_loss"],
            metrics={"eval_loss": results["finetuned_eval_loss"], "perplexity": results["finetuned_perplexity"]},
        )
        session.add_all([base_eval, finetuned_eval])

        await session.commit()
        print(f"base ModelVersion id={base_version.id} eval_loss={results['base_eval_loss']}")
        print(f"finetuned ModelVersion id={finetuned_version.id} eval_loss={results['finetuned_eval_loss']}")

        improvement = results["base_eval_loss"] - results["finetuned_eval_loss"]
        verdict = "IMPROVED" if improvement > 0 else "DID NOT IMPROVE (or regressed)"
        print(f"VERDICT: fine-tuned eval_loss vs base -> delta={improvement:.4f} ({verdict})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
