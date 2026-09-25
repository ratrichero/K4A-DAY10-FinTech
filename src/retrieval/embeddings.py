from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        if not model_name or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._validate_texts(texts)
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        self._validate_texts([text])
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding[0].tolist()

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> None:
        invalid = [index for index, text in enumerate(texts) if not isinstance(text, str) or not text.strip()]
        if invalid:
            raise ValueError(f"Embedding input contains empty or non-string text at positions: {invalid}.")
