from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(abstract_raw: str | None) -> str:
    if not abstract_raw:
        return ""
    text = re.sub(r"<[^>]+>", "", abstract_raw)
    return normalize_whitespace(text)


def _format_date_parts(date_parts: list[Any] | None) -> str:
    if not date_parts or not date_parts[0]:
        return "2026-01-01"
    parts = date_parts[0]
    year = int(parts[0]) if len(parts) > 0 else 2026
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    message = payload.get("message", {})
    items = message.get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list):
            title = " ".join(raw_title).strip()
        else:
            title = str(raw_title).strip()
        title = normalize_whitespace(title)

        summary = _clean_abstract(item.get("abstract"))

        authors_list: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = normalize_whitespace(f"{given} {family}".strip())
            if full_name:
                authors_list.append(full_name)
        if not authors_list:
            authors_list = ["Anonymous"]

        subjects = item.get("subject", [])
        categories = [normalize_whitespace(s) for s in subjects if s] if subjects else ["General"]
        primary_category = categories[0] if categories else "General"

        pub_data = item.get("published", {})
        published = _format_date_parts(pub_data.get("date-parts"))

        created_data = item.get("created", {})
        updated = created_data.get("date-time", published)
        if "T" in str(updated):
            updated = str(updated).split("T")[0]

        url = str(item.get("URL", f"https://doi.org/{paper_id}")).strip()

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors_list,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=str(updated),
            abs_url=url,
            pdf_url=url,
            comment=f"Crossref record {paper_id}",
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records. Co co che fallback offline."""
    payload: dict | None = None
    headers = {"User-Agent": "Day10-Data-Observability-Lab/1.0 (mailto:student@vinuni.edu.vn)"}
    params = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter

    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params=params,
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            payload = resp.json()
            write_json(settings.paths.raw_api_response, payload)
    except Exception:
        payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise RuntimeError(
                f"Cannot fetch from Crossref API and offline snapshot not found at {settings.paths.raw_api_response}"
            )

    records = parse_crossref_payload(payload)
    records_payload = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_payload)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    raw_data = read_json(path)
    return [PaperRecord(**item) for item in raw_data]
