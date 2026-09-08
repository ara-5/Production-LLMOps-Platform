"""A deliberately simple TF-IDF retriever over the fixed Northwind Cloud
corpus. No embeddings/vector DB needed — deterministic, free, fast, and
exactly reproducible for retrieval-quality metrics against a golden dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_CORPUS_PATH = Path(__file__).parent / "corpus" / "docs.json"


@dataclass
class RetrievedChunk:
    doc_id: str
    title: str
    text: str
    score: float


class Retriever:
    def __init__(self, corpus: list[dict]):
        self.corpus = corpus
        self._vectorizer = TfidfVectorizer(stop_words="english")
        corpus_texts = [f"{doc['title']}. {doc['text']}" for doc in corpus]
        self._matrix = self._vectorizer.fit_transform(corpus_texts)

    def retrieve(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked_idx = scores.argsort()[::-1][:k]
        return [
            RetrievedChunk(
                doc_id=self.corpus[i]["doc_id"],
                title=self.corpus[i]["title"],
                text=self.corpus[i]["text"],
                score=float(scores[i]),
            )
            for i in ranked_idx
        ]


def load_corpus() -> list[dict]:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


_retriever_singleton: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever_singleton
    if _retriever_singleton is None:
        _retriever_singleton = Retriever(load_corpus())
    return _retriever_singleton
