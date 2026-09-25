from __future__ import annotations

import logging
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("Phase1Pipeline")

    logger.info("=== STEP 1: Load Settings ===")
    settings = load_settings()

    logger.info("=== STEP 2: Ingest Raw Records (Crossref) ===")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    logger.info(f"Loaded {len(records)} raw records.")

    logger.info("=== STEP 3: Clean & Standardize Records ===")
    run_date = now_utc()
    clean_df = build_clean_dataframe(records, run_date)
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    logger.info(f"Cleaned dataset saved: {len(clean_df)} records to {settings.paths.clean_csv}")

    logger.info("=== STEP 4: Run Data Quality Gate (Great Expectations 1.x) & Freshness Observability ===")
    quality_report = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness_report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    logger.info(f"Quality gate: {quality_report['passed_checks']}/{quality_report['total_checks']} passed. Success = {quality_report['success']}")
    logger.info(f"Freshness: is_fresh = {freshness_report['is_fresh']}, rate = {freshness_report['freshness_rate_pct']}%")

    logger.info("=== STEP 5: Build ChromaDB Vector Index ===")
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info(f"ChromaDB baseline collection '{index.collection_name}' built and persisted.")

    logger.info("=== STEP 6: Build Evaluation Test Set ===")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
    logger.info(f"Evaluation test set ready at {settings.paths.eval_testset}")

    logger.info("=== STEP 7: Run Baseline Retrieval & QA Evaluation ===")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0)
    mean_f1 = eval_bundle.summary.get("mean_token_f1", 0.0)
    logger.info(f"Baseline evaluation completed: hit_rate = {hit_rate:.4f}, mean_token_f1 = {mean_f1:.4f}")

    logger.info("=== STEP 8: Generate Baseline Markdown Report ===")
    source_summary = {
        "run_date": run_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source_query": settings.source_query,
        "raw_records_count": len(records),
        "clean_records_count": len(clean_df),
    }
    metrics = {
        "hit_at_1": hit_rate,
        "hit_at_3": hit_rate,
        "mrr": hit_rate,
        "context_precision": eval_bundle.summary.get("judge_accuracy", 0.0),
        "faithfulness": eval_bundle.summary.get("judge_accuracy", 0.0),
        "answer_relevance": eval_bundle.summary.get("judge_accuracy", 0.0),
        "semantic_similarity": eval_bundle.summary.get("mean_judge_score", 0.0) / 5.0,
        "token_f1": mean_f1,
        "sample_count": eval_bundle.summary.get("samples", 10),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    logger.info(f"Phase 1 report saved at {settings.paths.baseline_report}")
    logger.info(">>> PHASE 1 BASELINE PIPELINE EXECUTED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    main()
