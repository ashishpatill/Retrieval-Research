from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List, Tuple

from retrieval_research.retrieval.bm25 import tokenize
from retrieval_research.schema import Chunk, Evidence


def _token_vector(token: str, dimensions: int) -> List[float]:
    vector = [0.0] * dimensions
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    for offset in range(0, min(len(digest), 12), 4):
        bucket = int.from_bytes(digest[offset : offset + 4], "big") % dimensions
        sign = 1.0 if digest[offset] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _dot(left: List[float], right: List[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class LateInteractionIndex:
    """Dependency-free ColBERT-style MaxSim baseline.

    This keeps a per-token representation and scores each query token by its
    best matching document token. A real ColBERT model can replace this class
    without changing the surrounding retrieval service contract.
    """

    def __init__(self, chunks: Iterable[Chunk], dimensions: int = 128, max_doc_tokens: int = 256):
        self.chunks = list(chunks)
        self.dimensions = dimensions
        self.max_doc_tokens = max_doc_tokens
        self.doc_tokens = [tokenize(chunk.text)[:max_doc_tokens] for chunk in self.chunks]
        self.doc_vectors = [
            [_token_vector(token, dimensions=dimensions) for token in tokens]
            for tokens in self.doc_tokens
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "late_interaction_maxsim",
            "dimensions": self.dimensions,
            "max_doc_tokens": self.max_doc_tokens,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "doc_tokens": self.doc_tokens,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LateInteractionIndex":
        chunks = [Chunk.from_dict(item) for item in payload.get("chunks", [])]
        index = cls(
            chunks,
            dimensions=payload.get("dimensions", 128),
            max_doc_tokens=payload.get("max_doc_tokens", 256),
        )
        if "doc_tokens" in payload:
            index.doc_tokens = payload["doc_tokens"]
            index.doc_vectors = [
                [_token_vector(token, dimensions=index.dimensions) for token in tokens]
                for tokens in index.doc_tokens
            ]
        return index

    def _score_doc(self, query_vectors: List[List[float]], doc_vectors: List[List[float]]) -> float:
        if not query_vectors or not doc_vectors:
            return 0.0
        total = 0.0
        for query_vector in query_vectors:
            total += max(_dot(query_vector, doc_vector) for doc_vector in doc_vectors)
        return total / len(query_vectors)

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        query_tokens = tokenize(query)
        query_vectors = [_token_vector(token, dimensions=self.dimensions) for token in query_tokens]
        scores: List[Tuple[int, float]] = []
        for idx, doc_vectors in enumerate(self.doc_vectors):
            score = self._score_doc(query_vectors, doc_vectors)
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
                    retrieval_path="late",
                    metadata={
                        "chunk_index": chunk.chunk_index,
                        "parent_section": chunk.parent_section,
                        "scorer": "maxsim",
                    },
                )
            )
        return evidence
