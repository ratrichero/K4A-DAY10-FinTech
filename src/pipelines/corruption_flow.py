from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json, write_text
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _frame_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> list of JSON-safe dicts (chuyen numpy types sang kieu Python goc)."""
    return json.loads(df.to_json(orient="records"))


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_clean_dataframe(settings: Settings) -> pd.DataFrame:
    if settings.paths.clean_json.exists():
        return pd.read_json(settings.paths.clean_json, convert_dates=False)
    return pd.read_csv(settings.paths.clean_csv)


def _load_test_set(settings: Settings) -> list[dict[str, Any]]:
    return list(read_json(settings.paths.eval_testset))


def _missing_baseline_artifacts(settings: Settings) -> list[str]:
    """Phase 2 phai chay SAU Phase 1: kiem tra cac artifact bat buoc tu baseline flow."""
    required: dict[str, Path] = {
        "data/clean/papers_clean.csv (clean corpus from Phase 1)": settings.paths.clean_csv,
        "data/results/baseline_metrics.json (baseline metrics from Phase 1)": settings.paths.baseline_metrics,
        "data/eval/test_set.json (benchmark test set from Phase 1)": settings.paths.eval_testset,
    }
    return [label for label, path in required.items() if not path.exists()]


def _repair_from_raw_snapshot(settings: Settings, run_date: datetime) -> pd.DataFrame:
    """Idempotent repair: build_clean_dataframe() lai tu raw snapshot, khong sua tay."""
    if settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
    elif settings.paths.raw_api_response.exists():
        records = parse_crossref_payload(read_json(settings.paths.raw_api_response))
    else:
        raise RuntimeError(
            "Raw snapshot not found: cannot repair idempotently. "
            f"Expected {settings.paths.raw_records_json} or {settings.paths.raw_api_response}."
        )
    return build_clean_dataframe(records, run_date=run_date)


def _write_fallback_comparison_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
) -> None:
    """Report du phong de pipeline van hoan thanh khi TV4 chua implement reporting."""
    lines = [
        "# Corruption & Repair Report (3-Way Comparison)",
        "",
        "> Fallback report: `generate_corruption_report` (observability/reporting.py, TV4)",
        "> is not implemented yet. Numbers below come directly from the pipeline run.",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| :--- | ---: | ---: | ---: |",
        f"| Retrieval hit rate | {float(baseline_metrics.get('retrieval_hit_rate', 0.0)):.2%} "
        f"| {float(corrupted_metrics.get('retrieval_hit_rate', 0.0)):.2%} "
        f"| {float(repaired_metrics.get('retrieval_hit_rate', 0.0)):.2%} |",
        f"| Mean token F1 | {float(baseline_metrics.get('mean_token_f1', 0.0)):.2%} "
        f"| {float(corrupted_metrics.get('mean_token_f1', 0.0)):.2%} "
        f"| {float(repaired_metrics.get('mean_token_f1', 0.0)):.2%} |",
        f"| Judge accuracy | {float(baseline_metrics.get('judge_accuracy', 0.0)):.2%} "
        f"| {float(corrupted_metrics.get('judge_accuracy', 0.0)):.2%} "
        f"| {float(repaired_metrics.get('judge_accuracy', 0.0)):.2%} |",
        f"| GX quality gate success | n/a | {corrupted_quality.get('success')} | {repaired_quality.get('success')} |",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def main() -> None:
    settings = load_settings()
    run_date = datetime.now(UTC)

    print("=" * 72)
    print("PHASE 2: CORRUPTION & IDEMPOTENT REPAIR FLOW")
    print("=" * 72)

    missing = _missing_baseline_artifacts(settings)
    if missing:
        print("[PREFLIGHT] Phase 1 artifacts missing - Phase 2 must run AFTER Phase 1:")
        for label in missing:
            print(f"  - missing: {label}")
        print("[PREFLIGHT] Run `python script/run_phase1.py` first, then re-run this script.")
        raise SystemExit(2)

    baseline_metrics = _load_json_dict(settings.paths.baseline_metrics)
    test_set = _load_test_set(settings)

    print(
        f"[1/9] Baseline state loaded: {len(test_set)} benchmark questions, "
        f"baseline hit rate = {float(baseline_metrics.get('retrieval_hit_rate', 0.0)):.2%}"
    )

    print("[2/9] Injecting 6 corruption scenarios into the clean dataset...")
    clean_df = _load_clean_dataframe(settings)
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, _frame_records(corrupted_df))
    print(f"      - corrupted corpus: {len(corrupted_df)} rows -> {settings.paths.corrupted_clean_csv.name}")

    print("[3/9] Building ChromaDB collection 'papers-corrupted'...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    print(f"      - collection: {corrupted_index.collection_name}")

    print("[4/9] Great Expectations gate on corrupted data (expected: FAIL)...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        report_path=settings.paths.quality_dir / "corrupted_freshness_report.json",
        report_name="corrupted",
    )
    print(
        f"      - GX success={corrupted_quality['success']} "
        f"({corrupted_quality['passed_checks']}/{corrupted_quality['total_checks']} checks passed)"
    )
    print(
        f"      - freshness is_fresh={corrupted_freshness['is_fresh']} "
        f"(stale {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']})"
    )

    print("[5/9] Evaluating the corrupted index on the same benchmark test set...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(
        f"      - hit rate={corrupted_eval.summary['retrieval_hit_rate']:.2%}, "
        f"token F1={corrupted_eval.summary['mean_token_f1']:.2%}"
    )

    print("[6/9] Idempotent repair: rebuilding clean data from the raw snapshot...")
    repaired_df = _repair_from_raw_snapshot(settings, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, _frame_records(repaired_df))
    print(f"      - repaired corpus: {len(repaired_df)} rows -> {settings.paths.repaired_clean_csv.name}")

    print("[7/9] Building ChromaDB collection 'papers-repaired'...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        report_path=settings.paths.quality_dir / "repaired_freshness_report.json",
        report_name="repaired",
    )
    print(f"      - GX success={repaired_quality['success']}")

    print("[8/9] Evaluating the repaired index on the same benchmark test set...")
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(
        f"      - hit rate={repaired_eval.summary['retrieval_hit_rate']:.2%}, "
        f"token F1={repaired_eval.summary['mean_token_f1']:.2%}"
    )

    print("[9/9] Generating the 3-way comparison report (Baseline vs Corrupted vs Repaired)...")
    try:
        generate_corruption_report(
            report_path=settings.paths.comparison_report,
            baseline_metrics=baseline_metrics,
            corrupted_metrics=corrupted_eval.summary,
            repaired_metrics=repaired_eval.summary,
            corrupted_quality=corrupted_quality,
            repaired_quality=repaired_quality,
            corrupted_freshness=corrupted_freshness,
            repaired_freshness=repaired_freshness,
        )
        report_source = "observability.reporting.generate_corruption_report"
    except NotImplementedError:
        _write_fallback_comparison_report(
            settings.paths.comparison_report,
            baseline_metrics=baseline_metrics,
            corrupted_metrics=corrupted_eval.summary,
            repaired_metrics=repaired_eval.summary,
            corrupted_quality=corrupted_quality,
            repaired_quality=repaired_quality,
        )
        report_source = "fallback report (generate_corruption_report not implemented yet - TV4 pending)"
    print(f"      - report: {settings.paths.comparison_report} ({report_source})")

    idempotent = len(repaired_df) == len(clean_df) and list(repaired_df["paper_id"]) == list(clean_df["paper_id"])
    baseline_hit = float(baseline_metrics.get("retrieval_hit_rate", 0.0))
    delta_hit = float(corrupted_eval.summary["retrieval_hit_rate"]) - baseline_hit
    recovered_hit = float(repaired_eval.summary["retrieval_hit_rate"]) - baseline_hit

    print("-" * 72)
    print("SUMMARY")
    print(
        f"  hit rate : baseline={baseline_hit:.2%} | "
        f"corrupted={float(corrupted_eval.summary['retrieval_hit_rate']):.2%} ({delta_hit:+.2%}) | "
        f"repaired={float(repaired_eval.summary['retrieval_hit_rate']):.2%} ({recovered_hit:+.2%})"
    )
    print(f"  silent failure caught by GX gate: corrupted success={corrupted_quality['success']}")
    print(
        f"  idempotent repair vs clean corpus: {'IDENTICAL' if idempotent else 'MISMATCH - check repair'} "
        f"({len(repaired_df)} rows)"
    )
    print("=" * 72)
