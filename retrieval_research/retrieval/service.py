from __future__ import annotations

import re
from typing import List, Tuple

from retrieval_research.retrieval.bm25 import BM25Index
from retrieval_research.retrieval.colpali import DEFAULT_COLPALI_MODEL, ColPaliPageIndex
from retrieval_research.retrieval.dense import DenseIndex
from retrieval_research.retrieval.graph import GraphIndex
from retrieval_research.retrieval.hybrid import reciprocal_rank_fusion
from retrieval_research.retrieval.planner import plan_query
from retrieval_research.retrieval.visual import VisualPageIndex, load_visual_index
from retrieval_research.schema import Evidence
from retrieval_research.storage import ArtifactStore


RETRIEVAL_MODES = ("bm25", "dense", "hybrid", "visual", "graph", "planner")

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _text_overlap(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    inter = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return inter / union if union else 0.0


def _has_negation(text: str) -> bool:
    terms = {"not", "no", "without", "never", "none"}
    return bool(_tokens(text) & terms)


def _consolidate_planner_hits(hits: List[Evidence], top_k: int, query_type: str, planner_reason: str) -> tuple[List[Evidence], dict]:
    by_chunk: dict[str, Evidence] = {}
    chunk_routes: dict[str, set[str]] = {}
    for item in hits:
        current = by_chunk.get(item.chunk_id)
        if current is None or item.score > current.score:
            by_chunk[item.chunk_id] = item
        chunk_routes.setdefault(item.chunk_id, set()).add(item.retrieval_path)

    ranked = sorted(by_chunk.values(), key=lambda item: item.score, reverse=True)
    selected = ranked[: max(top_k, 8)]
    redundancies = []
    conflicts = []

    # Detect near-duplicate evidence across chunk IDs on the same page.
    for idx, item in enumerate(selected):
        for other in selected[idx + 1 :]:
            if item.chunk_id == other.chunk_id:
                continue
            if not (set(item.page_numbers) & set(other.page_numbers)):
                continue
            overlap = _text_overlap(item.text, other.text)
            if overlap >= 0.72:
                redundancies.append((item.chunk_id, other.chunk_id, overlap))
            elif overlap >= 0.28 and _has_negation(item.text) != _has_negation(other.text):
                conflicts.append((item.chunk_id, other.chunk_id, overlap))

    redundant_ids = {pair[1] for pair in sorted(redundancies, key=lambda value: value[2], reverse=True)}
    kept = [item for item in ranked if item.chunk_id not in redundant_ids][:top_k]

    planner_hits = []
    for item in kept:
        planner_hits.append(
            Evidence(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                page_numbers=item.page_numbers,
                text=item.text,
                score=item.score,
                retrieval_path=f"planner:{item.retrieval_path}",
                metadata={
                    **item.metadata,
                    "query_type": query_type,
                    "planner_reason": planner_reason,
                    "source_paths": sorted(chunk_routes.get(item.chunk_id, set())),
                },
            )
        )

    merge_stats = {
        "input_hits": len(hits),
        "unique_chunks": len(by_chunk),
        "kept_hits": len(planner_hits),
        "redundancy_groups": len(redundancies),
        "conflicts_detected": len(conflicts),
        "redundancies": [
            {"kept_chunk": kept_id, "dropped_chunk": dropped_id, "overlap": round(overlap, 3)}
            for kept_id, dropped_id, overlap in redundancies[:8]
        ],
        "conflicts": [
            {"left_chunk": left_id, "right_chunk": right_id, "overlap": round(overlap, 3)}
            for left_id, right_id, overlap in conflicts[:8]
        ],
    }
    return planner_hits, merge_stats


def build_indexes(
    store: ArtifactStore,
    document_id: str,
    mode: str = "all",
    visual_backend: str = "baseline",
    colpali_model: str = DEFAULT_COLPALI_MODEL,
    device: str = "auto",
) -> List[str]:
    chunks = store.load_chunks(document_id)
    saved = []
    if mode in {"all", "bm25", "hybrid", "planner"}:
        bm25 = BM25Index(chunks)
        saved.append(str(store.save_index(document_id, "bm25", bm25.to_dict())))
    if mode in {"all", "dense", "hybrid", "planner"}:
        dense = DenseIndex(chunks)
        saved.append(str(store.save_index(document_id, "dense", dense.to_dict())))
    if mode in {"all", "visual", "planner"}:
        document = store.load_document(document_id)
        if visual_backend == "colpali":
            visual = ColPaliPageIndex.build(document, model_name=colpali_model, device=device)
        else:
            visual = VisualPageIndex(document)
        saved.append(str(store.save_index(document_id, "visual", visual.to_dict())))
    if mode in {"all", "graph", "planner"}:
        graph = GraphIndex(chunks)
        saved.append(str(store.save_index(document_id, "graph", graph.to_dict())))
    return saved


def search_document(
    store: ArtifactStore,
    document_id: str,
    query: str,
    mode: str = "hybrid",
    top_k: int = 5,
) -> Tuple[List[Evidence], List[dict]]:
    steps = []
    if mode == "bm25":
        index = BM25Index.from_dict(store.load_index(document_id, "bm25"))
        hits = index.search(query, top_k=top_k)
        steps.append({"path": "bm25", "document_id": document_id, "hits": len(hits)})
        return hits, steps

    if mode == "dense":
        index = DenseIndex.from_dict(store.load_index(document_id, "dense"))
        hits = index.search(query, top_k=top_k)
        steps.append({"path": "dense", "document_id": document_id, "hits": len(hits)})
        return hits, steps

    if mode == "hybrid":
        bm25 = BM25Index.from_dict(store.load_index(document_id, "bm25"))
        dense = DenseIndex.from_dict(store.load_index(document_id, "dense"))
        bm25_hits = bm25.search(query, top_k=max(top_k, 10))
        dense_hits = dense.search(query, top_k=max(top_k, 10))
        hits = reciprocal_rank_fusion(bm25_hits, dense_hits, top_k=top_k)
        steps.extend(
            [
                {"path": "bm25", "document_id": document_id, "hits": len(bm25_hits)},
                {"path": "dense", "document_id": document_id, "hits": len(dense_hits)},
                {"path": "hybrid", "document_id": document_id, "hits": len(hits), "fusion": "reciprocal_rank"},
            ]
        )
        return hits, steps

    if mode == "visual":
        index = load_visual_index(store.load_index(document_id, "visual"))
        hits = index.search(query, top_k=top_k)
        steps.append({"path": "visual", "document_id": document_id, "hits": len(hits)})
        return hits, steps

    if mode == "graph":
        index = GraphIndex.from_dict(store.load_index(document_id, "graph"))
        hits = index.search(query, top_k=top_k)
        steps.append({"path": "graph", "document_id": document_id, "hits": len(hits), "expansion": "chunk_graph"})
        return hits, steps

    if mode == "planner":
        plan = plan_query(query)
        all_hits: List[Evidence] = []
        steps.append({"path": "planner", "document_id": document_id, **plan.to_dict()})
        for route in plan.routes:
            route_settings = plan.route_settings.get(route, {})
            factor = float(route_settings.get("top_k_factor", 2.0))
            route_top_k = max(top_k, int(round(top_k * factor)))
            try:
                hits, route_steps = search_document(store, document_id, query, mode=route, top_k=route_top_k)
            except FileNotFoundError:
                steps.append({"path": route, "document_id": document_id, "hits": 0, "error": "missing_index"})
                continue
            steps.append(
                {
                    "path": "planner_route",
                    "document_id": document_id,
                    "route": route,
                    "requested_top_k": top_k,
                    "route_top_k": route_top_k,
                    "settings": route_settings,
                }
            )
            all_hits.extend(hits)
            steps.extend(route_steps)
        if not all_hits:
            return [], steps
        planner_hits, merge_stats = _consolidate_planner_hits(
            all_hits, top_k=top_k, query_type=plan.query_type, planner_reason=plan.reason
        )
        steps.append(
            {
                "path": "planner_merge",
                "document_id": document_id,
                "hits": len(planner_hits),
                "requested_top_k": top_k,
                "merge_strategy": plan.merge_strategy,
                **merge_stats,
            }
        )
        return planner_hits, steps

    raise ValueError(f"Unsupported retrieval mode: {mode}")


def search_corpus(
    store: ArtifactStore,
    document_ids: List[str],
    query: str,
    mode: str = "hybrid",
    top_k: int = 5,
) -> Tuple[List[Evidence], List[dict]]:
    evidence: List[Evidence] = []
    steps: List[dict] = []
    for document_id in document_ids:
        try:
            hits, doc_steps = search_document(store, document_id, query, mode=mode, top_k=top_k)
        except FileNotFoundError:
            steps.append({"path": mode, "document_id": document_id, "hits": 0, "error": "missing_index"})
            continue
        evidence.extend(hits)
        steps.extend(doc_steps)

    evidence.sort(key=lambda item: item.score, reverse=True)
    return evidence[:top_k], steps
