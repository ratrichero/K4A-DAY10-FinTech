from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo kiem tra chat luong du lieu su dung Great Expectations 1.x ephemeral mode."""
    context = gx.get_context(mode="ephemeral")
    data_source_name = f"pandas_{report_name}"
    data_source = context.data_sources.add_pandas(name=data_source_name)
    data_asset = data_source.add_dataframe_asset(name=f"asset_{report_name}")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(f"batch_{report_name}")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"suite_{report_name}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)

    overall_success = bool(validation_result.success)
    results_detail: list[dict[str, Any]] = []

    for res in validation_result.results:
        exp_type = res.expectation_config.type if res.expectation_config else "unknown"
        kwargs = res.expectation_config.kwargs if res.expectation_config else {}
        col = kwargs.get("column", "table")
        results_detail.append(
            {
                "expectation": exp_type,
                "column": col,
                "success": bool(res.success),
                "result": res.result,
            }
        )

    passed_count = sum(1 for r in results_detail if r["success"])
    failed_count = len(results_detail) - passed_count

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "total_checks": len(results_detail),
        "passed_checks": passed_count,
        "failed_checks": failed_count,
        "checks": results_detail,
    }

    output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    ensure_parent(output_path)
    write_json(output_path, report_payload)
    return report_payload


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
    report_name: str = "baseline",
) -> dict[str, Any]:
    """Tong hop freshness report cho dataset (rate bai qua han > 25% -> is_fresh = False)."""
    path = Path(report_path) if report_path else settings.paths.freshness_report
    ensure_parent(path)

    total_rows = len(df)
    stale_threshold = settings.freshness_threshold_days
    if total_rows > 0 and "age_days" in df.columns:
        stale_rows = int((pd.to_numeric(df["age_days"], errors="coerce").fillna(0) > stale_threshold).sum())
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
    else:
        stale_rows = 0
        latest_published = "N/A"
        oldest_published = "N/A"

    fresh_rows = total_rows - stale_rows
    freshness_rate = (fresh_rows / total_rows * 100.0) if total_rows > 0 else 0.0

    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "fresh_rows": fresh_rows,
        "stale_rate_pct": round(100.0 - freshness_rate, 2),
        "freshness_rate_pct": round(freshness_rate, 2),
        "stale_threshold_days": stale_threshold,
        "is_fresh": bool(round(freshness_rate, 2) >= 75.0),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
    }

    write_json(path, payload)
    return payload
