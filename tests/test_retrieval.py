from __future__ import annotations

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex


def test_chroma_baseline_index_search(settings: Settings):
    assert settings.paths.embeddings_json.exists(), "Baseline embeddings manifest must exist"
    index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)

    assert len(index.documents) == 24
    results = index.search("agentic multi-hop reasoning RAG", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top.paper_id.strip()
    assert top.title.strip()
    assert top.score > 0.0


def test_chroma_exact_lookup(settings: Settings):
    index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    first_doc = index.documents[0]
    match = index.lookup(first_doc["paper_id"])
    assert match is not None
    assert match["paper_id"] == first_doc["paper_id"]
