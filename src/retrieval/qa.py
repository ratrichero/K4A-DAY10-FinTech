from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if any(
        phrase in lowered
        for phrase in ("who authored", "list the authors", "who are the authors", "ai là tác giả", "tác giả của")
    ):
        return str(metadata.get("authors_joined", "")) or "Unknown"
    if any(
        phrase in lowered
        for phrase in ("when was", "publication date", "published on", "công bố", "xuất bản", "năm nào")
    ):
        return str(metadata.get("published", "")) or "Unknown"
    if any(
        phrase in lowered
        for phrase in (
            "what categories",
            "which categories",
            "what category",
            "thuộc lĩnh vực",
            "thuộc danh mục",
            "chủ đề nào",
        )
    ):
        return str(metadata.get("categories_joined", "")) or "Unknown"
    summary = str(metadata.get("summary", ""))
    return first_sentence(summary) if summary else "I don't know from the indexed corpus."


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")
    title_match = re.search(r"['\"]([^'\"]+)['\"]", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
