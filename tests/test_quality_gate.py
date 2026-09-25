from __future__ import annotations

import pandas as pd

from core.config import Settings
from observability.quality import build_freshness_report, run_data_quality_checks


def test_quality_gate_passes_on_clean_data(settings: Settings):
    assert settings.paths.clean_csv.exists(), "Clean CSV must exist"
    df = pd.read_csv(settings.paths.clean_csv)

    report = run_data_quality_checks(df, settings, report_name="test_clean")
    assert report["success"] is True, "Quality gate should pass on clean baseline data"
    assert report["passed_checks"] == 6, f"Expected 6 passed checks, got {report['passed_checks']}"
    assert report["failed_checks"] == 0


def test_freshness_sla(settings: Settings):
    assert settings.paths.clean_csv.exists(), "Clean CSV must exist"
    df = pd.read_csv(settings.paths.clean_csv)

    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    assert freshness["is_fresh"] is True, "Dataset should meet freshness SLA"
    assert freshness["freshness_rate_pct"] >= 75.0
