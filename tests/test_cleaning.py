from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from core.config import Settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records


def test_build_clean_dataframe(settings: Settings):
    records = load_raw_records(settings.paths.raw_records_json)
    now = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, now)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 24, "All 24 valid records should be cleaned"

    required_columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "authors_joined",
        "categories",
        "categories_joined",
        "primary_category",
        "published",
        "age_days",
        "summary_chars",
        "text_for_embedding",
    ]
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify no nulls in critical fields
    assert df["paper_id"].isnull().sum() == 0
    assert df["title"].isnull().sum() == 0
    assert df["text_for_embedding"].isnull().sum() == 0
    assert df["paper_id"].is_unique, "paper_id must be unique"

    # Verify embedding text 5-line structure
    sample_text = df.iloc[0]["text_for_embedding"]
    assert "Title:" in sample_text
    assert "Authors:" in sample_text
    assert "Published:" in sample_text
    assert "Categories:" in sample_text
    assert "Summary:" in sample_text
