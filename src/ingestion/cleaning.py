from __future__ import annotations

from datetime import UTC, datetime, timezone
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_published_date(pub_str: str) -> datetime:
    try:
        clean_date = pub_str.strip()[:10]
        dt = datetime.strptime(clean_date, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=timezone.utc)

    rows: list[dict] = []
    seen_ids: set[str] = set()

    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        if not paper_id or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not title or len(title) < 5:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if a]
        authors_joined = compact_join(authors, sep=", ")

        categories = [normalize_whitespace(c) for c in record.categories if c]
        categories_joined = compact_join(categories, sep=", ")
        primary_category = record.primary_category or (categories[0] if categories else "General")

        pub_dt = _parse_published_date(record.published)
        age_days = max(0, (run_date - pub_dt).days)
        published_str = pub_dt.strftime("%Y-%m-%d")

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        ).strip()

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
