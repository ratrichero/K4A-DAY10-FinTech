from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json

logger = logging.getLogger(__name__)


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | None = None,
    report_name: str = "baseline",
) -> dict[str, Any]:
    """Tong hop & kiem tra Freshness SLA cho DataFrame bai bao.

    Canh bao neu ty le bai bao cu (age_days > threshold_days, mac dinh 180) vuot 25%.
    Baseline ghi mac dinh vao `data/quality/freshness_report.json`; cac trang thai
    khac (corrupted/repaired/...) ghi file rieng theo `report_name` de khong ghi de
    ket qua cua nhau. Truyen `report_path` de ghi de duong dan (tuong thich cu).
    """
    threshold_days = getattr(settings, "freshness_threshold_days", 180)
    total_rows = len(df)

    if total_rows == 0 or "age_days" not in df.columns:
        latest_published = ""
        oldest_published = ""
        stale_rows = 0
        stale_ratio = 0.0
        is_fresh = True
    else:
        stale_rows = int((df["age_days"] > threshold_days).sum())
        stale_ratio = float(stale_rows / total_rows)
        is_fresh = bool(stale_ratio <= 0.25)

        pub_series = df["published"].dropna().astype(str) if "published" in df.columns else pd.Series(dtype=str)
        latest_published = str(pub_series.max()) if not pub_series.empty else ""
        oldest_published = str(pub_series.min()) if not pub_series.empty else ""

    payload: dict[str, Any] = {
        "report_name": report_name,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "stale_rate_pct": round(100.0 * stale_ratio, 2),
        "freshness_rate_pct": round(100.0 * (1.0 - stale_ratio), 2),
        "freshness_threshold_days": threshold_days,
        "max_stale_ratio_allowed": 0.25,
        "is_fresh": is_fresh,
    }

    if report_path is None:
        if report_name == "baseline":
            report_path = settings.paths.quality_dir / "freshness_report.json"
        else:
            report_path = settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    write_json(Path(report_path), payload)
    return payload


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay Data Quality Gate bang Great Expectations 1.x (ephemeral context).

    6 expectations: row count 5-5000; paper_id/title/text_for_embedding not null;
    paper_id unique; summary >= 30 ky tu.
    """
    context = gx.get_context(mode="ephemeral")

    data_source_name = f"papers_source_{report_name}"
    data_asset_name = f"papers_asset_{report_name}"
    batch_def_name = f"papers_batch_{report_name}"

    data_source = context.data_sources.add_pandas(name=data_source_name)
    data_asset = data_source.add_dataframe_asset(name=data_asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_def_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Tao Expectation Suite
    suite_name = f"papers_suite_{report_name}"
    suite = gx.ExpectationSuite(name=suite_name)

    # Expectation 1: Row count tu 5 den 5000
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))

    # Expectation 2: paper_id, title, text_for_embedding khong null
    for col in ["paper_id", "title", "text_for_embedding"]:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # Expectation 3: paper_id unique
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))

    # Expectation 4: summary do dai toi thieu 30 ky tu
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    context.suites.add(suite)

    # 3. Thuc thi Validation
    try:
        validation_results = batch.validate(suite)
    except Exception:
        val_def_name = f"papers_validation_{report_name}"
        validation_def = gx.ValidationDefinition(
            name=val_def_name,
            data=batch_def,
            suite=suite,
        )
        context.validation_definitions.add(validation_def)
        validation_results = validation_def.run(batch_parameters={"dataframe": df})

    gx_success = bool(getattr(validation_results, "success", False))

    # 4. Freshness SLA theo tung trang thai (file rieng, khong ghi de nhau)
    freshness = build_freshness_report(df, settings, report_name=report_name)

    overall_success = gx_success and freshness["is_fresh"]

    results_dict = validation_results.to_json_dict() if hasattr(validation_results, "to_json_dict") else {}
    validation_items = results_dict.get("results", []) if isinstance(results_dict, dict) else []
    total_checks = len(validation_items)
    passed_checks = sum(1 for item in validation_items if bool(item.get("success")))
    failed_checks = total_checks - passed_checks

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "row_count": int(len(df)),
        "success": overall_success,
        "gx_success": gx_success,
        "freshness": freshness,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "validation_results": results_dict,
    }

    # 5. Luu bao cao quality check vao dia
    quality_dir = settings.paths.quality_dir
    quality_dir.mkdir(parents=True, exist_ok=True)

    if report_name == "baseline":
        save_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        save_path = settings.paths.corrupted_quality_report
    else:
        save_path = quality_dir / f"{report_name}_quality_report.json"

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)

    return report_payload
