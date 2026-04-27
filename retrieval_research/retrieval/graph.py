from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from retrieval_research.schema import Chunk, Evidence


TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


class GraphIndex:
    def __init__(self, chunks: List[Chunk], edges: Dict[str, List[dict]] | None = None):
        self.chunks = chunks
        self.by_id = {chunk.id: chunk for chunk in chunks}
        self.edges = edges or self._build_edges(chunks)

    @staticmethod
    def _build_edges(chunks: List[Chunk]) -> Dict[str, List[dict]]:
        edges: dict[str, list[dict]] = defaultdict(list)
        by_page: dict[int, list[Chunk]] = defaultdict(list)
        by_section: dict[str, list[Chunk]] = defaultdict(list)

        for chunk in chunks:
            for page in chunk.page_numbers:
                by_page[page].append(chunk)
            if chunk.parent_section:
                by_section[chunk.parent_section].append(chunk)

        ordered = sorted(chunks, key=lambda chunk: chunk.chunk_index)
        for left, right in zip(ordered, ordered[1:]):
            edges[left.id].append({"target": right.id, "relation": "next_chunk", "weight": 0.4})
            edges[right.id].append({"target": left.id, "relation": "previous_chunk", "weight": 0.4})

        for page, page_chunks in by_page.items():
            ids = [chunk.id for chunk in page_chunks]
            for chunk_id in ids:
                for other_id in ids:
                    if chunk_id != other_id:
                        edges[chunk_id].append({"target": other_id, "relation": "same_page", "page": page, "weight": 0.3})

        for section, section_chunks in by_section.items():
            ids = [chunk.id for chunk in section_chunks]
            for chunk_id in ids:
                for other_id in ids:
                    if chunk_id != other_id:
                        edges[chunk_id].append(
                            {"target": other_id, "relation": "same_section", "section": section, "weight": 0.5}
                        )

        return dict(edges)

    def to_dict(self) -> dict:
        return {
            "type": "graph",
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "edges": self.edges,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GraphIndex":
        return cls(
            [Chunk.from_dict(item) for item in payload.get("chunks", [])],
            edges=payload.get("edges", {}),
        )

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        seeds = []
        for chunk in self.chunks:
            chunk_tokens = _tokens(chunk.text)
            overlap = len(query_tokens & chunk_tokens)
            if overlap:
                seeds.append((chunk, overlap / max(len(query_tokens), 1)))

        seeds.sort(key=lambda item: item[1], reverse=True)
        scores: dict[str, float] = {}
        paths: dict[str, list[str]] = {}

        for chunk, score in seeds[: max(top_k, 8)]:
            scores[chunk.id] = max(scores.get(chunk.id, 0.0), score)
            paths.setdefault(chunk.id, []).append("seed")
            for edge in self.edges.get(chunk.id, []):
                target_id = edge["target"]
                propagated = score * float(edge.get("weight", 0.25))
                if propagated > scores.get(target_id, 0.0):
                    scores[target_id] = propagated
                paths.setdefault(target_id, []).append(edge.get("relation", "linked"))

        ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        evidence = []
        for chunk_id in ranked_ids:
            chunk = self.by_id.get(chunk_id)
            if not chunk:
                continue
            evidence.append(
                Evidence(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    page_numbers=chunk.page_numbers,
                    text=chunk.text,
                    score=scores[chunk_id],
                    retrieval_path="graph",
                    metadata={**chunk.metadata, "graph_relations": sorted(set(paths.get(chunk_id, [])))},
                )
            )
        return evidence
