from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import ensure_parent, write_json

_NOISE_TOKENS = " qzxjwkvv noiseplaceholder zqxjkw"


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    """Giu dung dinh dang 5 dong theo Data Contract trong mydoc/nhiemvu.md."""
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    ).strip()


def _recompute_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(_rebuild_text_for_embedding, axis=1)
    return df


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Tiem 6 kich ban loi vao clean dataframe va ghi corruption log.

    Kich ban (theo mydoc/nhiemvu.md - TV2):
      1. drop_latest_records : bo 20% bai moi nhat.
      2. blank_summary       : xoa trang tom tat mot so dong.
      3. inject_noise        : chen chuoi vo nghia vao tom tat.
      4. truncate_title      : cat title xuong < 8 ky tu.
      5. stale_date          : lui `published` ve 365 ngay truoc.
      6. duplicate_rows      : nhan doi mot so dong.

    Chon vi tri dong deterministic (khong random) de corruption log va ket qua
    chay lai luon khop nhau (idempotent-friendly).
    """
    corrupted = df.copy().reset_index(drop=True)
    scenarios: list[dict[str, Any]] = []
    rows_before = len(corrupted)

    # ---- 1. Drop latest records (df sap xep published giam dan -> head la moi nhat)
    n_drop = max(1, math.ceil(rows_before * 0.2))
    dropped_ids = corrupted.head(n_drop)["paper_id"].tolist()
    corrupted = corrupted.iloc[n_drop:].reset_index(drop=True)
    scenarios.append(
        {
            "scenario": "drop_latest_records",
            "description": f"Dropped the {n_drop} most recent papers (20% of corpus).",
            "rows_before": rows_before,
            "rows_affected": n_drop,
            "affected_paper_ids": dropped_ids,
        }
    )

    # ---- 2. Blank summary (moi dong thu 4, dem tu vi tri 1)
    blank_positions = list(range(1, len(corrupted), 4))
    blank_ids = corrupted.loc[blank_positions, "paper_id"].tolist()
    corrupted.loc[blank_positions, "summary"] = ""
    scenarios.append(
        {
            "scenario": "blank_summary",
            "description": f"Blanked the summary of {len(blank_positions)} rows (every 4th row).",
            "rows_affected": len(blank_positions),
            "affected_paper_ids": blank_ids,
        }
    )

    # ---- 3. Inject noise (moi dong thu 5, dem tu vi tri 2, khong trung dong blank)
    noise_positions = [p for p in range(2, len(corrupted), 5) if p not in blank_positions]
    noise_ids = corrupted.loc[noise_positions, "paper_id"].tolist()
    corrupted.loc[noise_positions, "summary"] = (
        corrupted.loc[noise_positions, "summary"].astype(str) + _NOISE_TOKENS
    )
    scenarios.append(
        {
            "scenario": "inject_noise",
            "description": f"Injected meaningless noise tokens into {len(noise_positions)} summaries.",
            "rows_affected": len(noise_positions),
            "affected_paper_ids": noise_ids,
        }
    )

    # ---- 4. Truncate title (< 8 ky tu) cho 3 dong cuoi
    truncate_positions = list(range(max(0, len(corrupted) - 3), len(corrupted)))
    truncate_ids = corrupted.loc[truncate_positions, "paper_id"].tolist()
    corrupted.loc[truncate_positions, "title"] = (
        corrupted.loc[truncate_positions, "title"].astype(str).str.slice(0, 6)
    )
    scenarios.append(
        {
            "scenario": "truncate_title",
            "description": f"Truncated titles to < 8 chars on {len(truncate_positions)} rows.",
            "rows_affected": len(truncate_positions),
            "affected_paper_ids": truncate_ids,
        }
    )

    # ---- 5. Stale date (lui published ve 365 ngay truoc) cho moi dong thu 6
    stale_positions = list(range(3, len(corrupted), 6))
    stale_ids = corrupted.loc[stale_positions, "paper_id"].tolist()
    if stale_positions:
        parsed = pd.to_datetime(corrupted.loc[stale_positions, "published"], format="%Y-%m-%d")
        corrupted.loc[stale_positions, "published"] = (
            parsed - pd.Timedelta(days=365)
        ).dt.strftime("%Y-%m-%d")
        corrupted.loc[stale_positions, "age_days"] = (
            pd.to_numeric(corrupted.loc[stale_positions, "age_days"]) + 365
        ).astype("int64")
    scenarios.append(
        {
            "scenario": "stale_date",
            "description": f"Shifted `published` back 365 days on {len(stale_positions)} rows.",
            "rows_affected": len(stale_positions),
            "affected_paper_ids": stale_ids,
        }
    )

    # ---- 6. Duplicate rows (nhan doi 2 dong dau)
    duplicate_positions = list(range(min(2, len(corrupted))))
    duplicated_ids = corrupted.loc[duplicate_positions, "paper_id"].tolist()
    if duplicate_positions:
        corrupted = pd.concat([corrupted, corrupted.iloc[duplicate_positions]], ignore_index=True)
    scenarios.append(
        {
            "scenario": "duplicate_rows",
            "description": f"Duplicated {len(duplicate_positions)} rows (first rows of the corpus).",
            "rows_affected": len(duplicate_positions),
            "affected_paper_ids": duplicated_ids,
        }
    )

    # ---- Rebuild cac cot phu sinh (text_for_embedding, summary_chars)
    corrupted = _recompute_derived_columns(corrupted)

    log_payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_rows_before": rows_before,
        "total_rows_after": len(corrupted),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
    log_path = output_log_path
    ensure_parent(log_path)
    write_json(log_path, log_payload)
    return corrupted
