from __future__ import annotations

from core.config import Settings
from core.utils import read_json
from ingestion.crossref import PaperRecord, load_raw_records, parse_crossref_payload


def test_offline_raw_snapshot_exists(settings: Settings):
    assert settings.paths.raw_api_response.exists(), "Raw API response snapshot must exist"
    assert settings.paths.raw_records_json.exists(), "Raw records JSON snapshot must exist"


def test_parse_crossref_payload(settings: Settings):
    payload = read_json(settings.paths.raw_api_response)
    records = parse_crossref_payload(payload)
    assert len(records) >= 10, f"Expected at least 10 records, got {len(records)}"
    for r in records:
        assert isinstance(r, PaperRecord)
        assert r.paper_id.strip(), "paper_id must not be empty"
        assert r.title.strip(), "title must not be empty"
        assert len(r.authors) > 0, "authors list must not be empty"
        assert r.published.strip(), "published date must not be empty"


def test_load_raw_records(settings: Settings):
    records = load_raw_records(settings.paths.raw_records_json)
    assert len(records) == 24, f"Expected exactly 24 records from standard snapshot, got {len(records)}"
    first = records[0]
    assert hasattr(first, "paper_id")
    assert hasattr(first, "title")
    assert hasattr(first, "summary")
