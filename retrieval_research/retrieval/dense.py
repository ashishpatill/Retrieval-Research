from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List, Tuple

from retrieval_research.retrieval.bm25 import tokenize
from retrieval_research.schema import Chunk, Evidence


def _term_weight(term: str) -> float:
    # A deterministic pseudo-IDF-ish weight. This is a local baseline, not a
    # replacement for real embedding models planned for later roadmap phases.
    digest = hashlib.sha1(term.encode("utf-8")).digest()
    return 0.75 + (digest[0] / 255.0)


def hashed_embedding(text: str, dimensions: int = 384) -> List[float]:
    vector = [0.0] * dimensions
    for term in tokenize(text):
        digest = hashlib.sha1(term.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign * _term_weight(term)

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(left * right for left, right in zip(a, b))


class DenseIndex:
    def __init__(self, chunks: Iterable[Chunk], dimensions: int = 384):
        self.chunks = list(chunks)
        self.dimensions = dimensions
        self.vectors = [hashed_embedding(chunk.text, dimensions=dimensions) for chunk in self.chunks]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "hashed_dense",
            "dimensions": self.dimensions,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "vectors": self.vectors,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DenseIndex":
        chunks = [Chunk.from_dict(item) for item in payload.get("chunks", [])]
        index = cls(chunks, dimensions=payload.get("dimensions", 384))
        if "vectors" in payload:
            index.vectors = payload["vectors"]
        return index

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        query_vector = hashed_embedding(query, dimensions=self.dimensions)
        scores: List[Tuple[int, float]] = []
        for idx, vector in enumerate(self.vectors):
            score = cosine(query_vector, vector)
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        evidence = []
        for idx, score in scores[:top_k]:
            chunk = self.chunks[idx]
            evidence.append(
                Evidence(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    page_numbers=chunk.page_numbers,
                    text=chunk.text,
                    score=score,
                    retrieval_path="dense",
                    metadata={"chunk_index": chunk.chunk_index, "parent_section": chunk.parent_section},
                )
            )
        return evidence
