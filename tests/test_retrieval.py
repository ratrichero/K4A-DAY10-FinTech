from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from core.config import Settings, load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.llm import build_llm
from retrieval.qa import answer_question


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


class FakeEmbeddings:
    """Small deterministic embedding model for offline retrieval tests."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @staticmethod
    def _embed(text: str) -> list[float]:
        lowered = text.lower()
        return [
            float(lowered.count("cat")),
            float(lowered.count("dog")),
            float(lowered.count("finance")),
            0.1,
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": "10.1000/cats",
                "title": "Semantic Search for Cats",
                "published": "2026-01-10T00:00:00Z",
                "authors_joined": "Ada Nguyen, Minh Tran",
                "categories_joined": "Information Retrieval",
                "summary": "Cats improve the retrieval benchmark. A second sentence is ignored.",
                "abs_url": "https://doi.org/10.1000/cats",
                "pdf_url": "https://example.test/cats.pdf",
                "text_for_embedding": "cat cat semantic retrieval benchmark",
            },
            {
                "paper_id": "10.1000/dogs",
                "title": "Observability for Dogs",
                "published": "2026-02-11T00:00:00Z",
                "authors_joined": "Lan Pham",
                "categories_joined": "Data Observability",
                "summary": "Dogs provide an observability example.",
                "abs_url": "https://doi.org/10.1000/dogs",
                "pdf_url": "https://example.test/dogs.pdf",
                "text_for_embedding": "dog dog data observability",
            },
        ]
    )


class StubIndex:
    def __init__(self, result: SearchResult | None):
        self.result = result
        self.exact = None

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        return [self.result] if self.result else []

    def lookup(self, value: str):
        return self.exact


class RetrievalIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.settings = load_settings(self.project_dir)
        self.indexes: list[LocalEmbeddingIndex] = []
        self.embedding_patch = patch("retrieval.index.MiniLMEmbeddings", FakeEmbeddings)
        self.embedding_patch.start()

    def tearDown(self) -> None:
        for index in reversed(self.indexes):
            index.close()
        self.embedding_patch.stop()
        self.temp_dir.cleanup()

    def build_index(self, *args, **kwargs) -> LocalEmbeddingIndex:
        index = LocalEmbeddingIndex.build(*args, **kwargs)
        self.indexes.append(index)
        return index

    def load_index(self, *args, **kwargs) -> LocalEmbeddingIndex:
        index = LocalEmbeddingIndex.load(*args, **kwargs)
        self.indexes.append(index)
        return index

    def test_build_search_lookup_and_load_round_trip(self) -> None:
        index = self.build_index(sample_dataframe(), self.settings)

        self.assertEqual(index.collection.count(), 2)
        self.assertEqual(index.collection_name, "papers-baseline")
        self.assertEqual(index.lookup("10.1000/CATS")["title"], "Semantic Search for Cats")
        self.assertEqual(index.lookup("semantic search for cats")["paper_id"], "10.1000/cats")

        results = index.search("cats", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].paper_id, "10.1000/cats")
        self.assertGreaterEqual(results[0].score, 0.0)
        self.assertLessEqual(results[0].score, 1.0)

        loaded = self.load_index(self.settings)
        self.assertEqual(loaded.collection_name, index.collection_name)
        self.assertEqual(loaded.collection.count(), 2)

    def test_rebuild_is_idempotent_and_collections_are_isolated(self) -> None:
        baseline = self.build_index(sample_dataframe(), self.settings)
        corrupted = self.build_index(
            sample_dataframe(),
            self.settings,
            self.settings.paths.corrupted_embeddings_json,
        )

        rebuilt = self.build_index(sample_dataframe().head(1), self.settings)

        self.assertEqual(baseline.collection_name, "papers-baseline")
        self.assertEqual(corrupted.collection_name, "papers-corrupted")
        self.assertEqual(rebuilt.collection.count(), 1)
        self.assertEqual(corrupted.collection.count(), 2)

    def test_empty_collection_and_input_validation(self) -> None:
        empty = sample_dataframe().head(0)
        index = self.build_index(empty, self.settings)

        self.assertEqual(index.search("anything"), [])
        with self.assertRaisesRegex(ValueError, "top_k"):
            index.search("anything", top_k=0)
        with self.assertRaisesRegex(ValueError, "query"):
            index.search("   ")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            self.build_index(pd.DataFrame({"paper_id": ["x"]}), self.settings)

    def test_duplicate_paper_ids_remain_indexable_for_corruption_flow(self) -> None:
        duplicated = pd.concat([sample_dataframe().head(1)] * 2, ignore_index=True)
        index = self.build_index(duplicated, self.settings)
        self.assertEqual(index.collection.count(), 2)


class RetrievalQATests(unittest.TestCase):
    def setUp(self) -> None:
        metadata = {
            "paper_id": "10.1000/cats",
            "title": "Semantic Search for Cats",
            "published": "2026-01-10T00:00:00Z",
            "authors_joined": "Ada Nguyen, Minh Tran",
            "categories_joined": "Information Retrieval",
            "summary": "Cats improve the retrieval benchmark. A second sentence is ignored.",
        }
        self.result = SearchResult(
            paper_id=metadata["paper_id"],
            title=metadata["title"],
            score=1.0,
            content="cat semantic retrieval",
            metadata=metadata,
        )
        self.settings = load_settings(Path.cwd())

    def test_answers_supported_question_types_in_english_and_vietnamese(self) -> None:
        index = StubIndex(self.result)
        cases = {
            "Who authored 'Semantic Search for Cats'?": "Ada Nguyen, Minh Tran",
            "Nghiên cứu 'Semantic Search for Cats' được công bố năm nào?": "2026-01-10T00:00:00Z",
            "Công trình 'Semantic Search for Cats' thuộc lĩnh vực nào?": "Information Retrieval",
            "Summarize 'Semantic Search for Cats'.": "Cats improve the retrieval benchmark.",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                answer = answer_question(question, self.settings, index)
                self.assertEqual(answer.answer, expected)
                self.assertEqual(answer.retrieved_doc_ids, ["10.1000/cats"])

    def test_no_results_and_invalid_question_are_safe(self) -> None:
        index = StubIndex(None)
        answer = answer_question("Unknown paper?", self.settings, index)
        self.assertEqual(answer.answer, "I don't know from the indexed corpus.")
        self.assertEqual(answer.retrieved_doc_ids, [])
        with self.assertRaisesRegex(ValueError, "question"):
            answer_question("", self.settings, index)


class EmbeddingAndAgentTests(unittest.TestCase):
    def test_embedding_validation_rejects_empty_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "positions"):
            MiniLMEmbeddings._validate_texts(["valid", " "])

    def test_mock_llm_and_agent_smoke_test(self) -> None:
        settings = replace(load_settings(Path.cwd()), llm_provider="mock", model_name="mock")
        llm = build_llm(settings)
        self.assertTrue(llm.invoke("hello").content)

        agent = build_agent(settings, StubIndex(None))
        self.assertIn("mock response", run_agent_question(agent, "What is indexed?").lower())
        with self.assertRaisesRegex(ValueError, "question"):
            run_agent_question(agent, " ")


if __name__ == "__main__":
    unittest.main()
