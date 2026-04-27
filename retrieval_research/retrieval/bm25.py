from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from retrieval_research.schema import Chunk, Evidence


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self, chunks: Iterable[Chunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks = list(chunks)
        self.doc_freq: Dict[str, int] = defaultdict(int)
        self.term_freqs: List[Counter] = []
        self.lengths: List[int] = []
        self.avgdl = 0.0
        self._build()

    def _build(self) -> None:
        total_len = 0
        for chunk in self.chunks:
            terms = tokenize(chunk.text)
            freqs = Counter(terms)
            self.term_freqs.append(freqs)
            self.lengths.append(len(terms))
            total_len += len(terms)
            for term in freqs:
                self.doc_freq[term] += 1
        self.avgdl = total_len / len(self.chunks) if self.chunks else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "bm25",
            "k1": self.k1,
            "b": self.b,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BM25Index":
        chunks = [Chunk.from_dict(item) for item in payload.get("chunks", [])]
        return cls(chunks, k1=payload.get("k1", 1.5), b=payload.get("b", 0.75))

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        if not self.chunks:
            return []

        query_terms = tokenize(query)
        scores: List[Tuple[int, float]] = []
        n_docs = len(self.chunks)

        for idx, freqs in enumerate(self.term_freqs):
            score = 0.0
            doc_len = self.lengths[idx] or 1
            for term in query_terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / (self.avgdl or 1))
                score += idf * ((tf * (self.k1 + 1)) / denom)
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
                    retrieval_path="bm25",
                    metadata={"chunk_index": chunk.chunk_index, "parent_section": chunk.parent_section},
                )
            )
        return evidence
