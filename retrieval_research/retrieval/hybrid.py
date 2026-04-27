from __future__ import annotations

from typing import Dict, Iterable, List

from retrieval_research.schema import Evidence


def _rank_scores(evidence: Iterable[Evidence], weight: float) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for rank, item in enumerate(evidence, 1):
        scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + weight / (60 + rank)
    return scores


def reciprocal_rank_fusion(
    bm25_hits: List[Evidence],
    dense_hits: List[Evidence],
    top_k: int = 5,
    bm25_weight: float = 1.0,
    dense_weight: float = 1.0,
) -> List[Evidence]:
    by_chunk: Dict[str, Evidence] = {}
    scores: Dict[str, float] = {}

    for item in bm25_hits + dense_hits:
        by_chunk.setdefault(item.chunk_id, item)

    for chunk_id, score in _rank_scores(bm25_hits, bm25_weight).items():
        scores[chunk_id] = scores.get(chunk_id, 0.0) + score
    for chunk_id, score in _rank_scores(dense_hits, dense_weight).items():
        scores[chunk_id] = scores.get(chunk_id, 0.0) + score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    fused = []
    for chunk_id, score in ranked[:top_k]:
        item = by_chunk[chunk_id]
        fused.append(
            Evidence(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                page_numbers=item.page_numbers,
                text=item.text,
                score=score,
                retrieval_path="hybrid",
                metadata={**item.metadata, "fusion": "reciprocal_rank"},
            )
        )
    return fused
