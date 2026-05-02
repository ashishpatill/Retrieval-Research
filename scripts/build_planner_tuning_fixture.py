from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval_research.chunking import chunk_document
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import DEFAULT_PLANNER_RERANK, DEFAULT_RERANK_OVERLAP_WEIGHT, DEFAULT_ROUTE_VOTE_BONUS, build_indexes
from retrieval_research.storage import ArtifactStore

CORPUS_DIR = ROOT / "datasets" / "corpora" / "planner_tuning"
MANIFEST_PATH = ROOT / "data" / "generated" / "planner_tuning_sweep.local.json"


QUERIES: List[Dict[str, Any]] = [
    {
        "query": "Compare planner routing and route vote behavior across the corpus.",
        "expected_terms": ["planner", "route", "vote"],
        "expected_entities": ["Retrieval Planner", "Route Vote"],
        "expected_sections": ["Planner Routing"],
    },
    {
        "query": "Which notes describe graph expansion for cross-document context?",
        "expected_terms": ["graph", "cross-document", "context"],
        "expected_entities": ["Knowledge Graph", "Graph Expansion"],
        "expected_sections": ["Graph Expansion"],
    },
    {
        "query": "Summarize the differences between hybrid and graph retrieval behavior.",
        "expected_terms": ["hybrid", "graph", "retrieval"],
        "expected_entities": ["Hybrid Retrieval", "Graph Retrieval"],
    },
    {
        "query": "Where are rerank overlap weights discussed?",
        "expected_terms": ["rerank", "overlap", "weight"],
        "expected_entities": ["Overlap Rerank"],
    },
    {
        "query": "What corpus evidence mentions citation support and answerability?",
        "expected_terms": ["citation", "support", "answerability"],
        "expected_entities": ["Citation Support", "Answerability"],
    },
    {
        "query": "Find references to table-heavy retrieval and visual routing.",
        "expected_terms": ["table", "visual", "routing"],
        "expected_entities": ["Visual Retrieval"],
    },
    {
        "query": "Which document links confidence calibration to planner tuning?",
        "expected_terms": ["confidence", "calibration", "planner"],
        "expected_entities": ["Confidence Calibration"],
    },
    {
        "query": "Identify the section that discusses shared entities across documents.",
        "expected_terms": ["shared", "entities", "documents"],
        "expected_entities": ["Shared Entities"],
        "expected_references": ["doi:10.1234/example", "arxiv:2401.12345"],
    },
    {
        "query": "What notes describe evaluation manifests and sweep variants?",
        "expected_terms": ["manifest", "sweep", "variants"],
        "expected_entities": ["Planner Sweep"],
    },
    {
        "query": "Find guidance about unresolved ambiguity and follow-up retrieval.",
        "expected_terms": ["ambiguity", "follow-up", "retrieval"],
        "expected_entities": ["Ambiguity Handling"],
    },
    {
        "query": "Which artifact should persist extracted sections, entities, and references?",
        "expected_terms": ["knowledge_graph.json", "sections", "entities", "references"],
    },
    {
        "query": "Where is route vote compared with score max merging?",
        "expected_terms": ["route_vote", "score_max", "merging"],
        "expected_entities": ["Route Vote", "Score Max"],
    },
]


def build_manifest(document_ids: List[str]) -> Dict[str, Any]:
    return {
        "document_ids": document_ids,
        "planner_merge_strategy": "score_max",
        "planner_rerank": DEFAULT_PLANNER_RERANK,
        "planner_route_vote_bonus": DEFAULT_ROUTE_VOTE_BONUS,
        "planner_rerank_overlap_weight": DEFAULT_RERANK_OVERLAP_WEIGHT,
        "planner_sweep": [
            {"name": "score_base", "merge_strategy": "score_max", "rerank": False},
            {
                "name": "score_rerank_soft",
                "merge_strategy": "score_max",
                "rerank": True,
                "rerank_overlap_weight": 0.10,
            },
            {
                "name": "route_vote_mid",
                "merge_strategy": "route_vote",
                "rerank": False,
                "route_vote_bonus": 0.08,
            },
            {
                "name": "route_vote_rerank_mid",
                "merge_strategy": "route_vote",
                "rerank": True,
                "route_vote_bonus": 0.08,
                "rerank_overlap_weight": 0.15,
            },
            {
                "name": "route_vote_rerank_strong",
                "merge_strategy": "route_vote",
                "rerank": True,
                "route_vote_bonus": 0.12,
                "rerank_overlap_weight": 0.25,
            },
        ],
        "queries": QUERIES,
    }


def main() -> None:
    store = ArtifactStore(str(ROOT / "data"))
    document_ids: List[str] = []

    for source in sorted(CORPUS_DIR.glob("*.md")):
        document = ingest_path(str(source), store=store)
        chunks = chunk_document(document, max_words=70, overlap_words=8)
        store.save_chunks(document.id, chunks)
        build_indexes(store, document.id, mode="all")
        document_ids.append(document.id)
        print(f"{source.name}: {document.id} ({len(chunks)} chunks)")

    if not document_ids:
        raise SystemExit(f"No Markdown files found in {CORPUS_DIR}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(build_manifest(document_ids), indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {MANIFEST_PATH.relative_to(ROOT)}")
    print(
        "run: python3 -m retrieval_research.cli eval "
        f"{MANIFEST_PATH.relative_to(ROOT)} --modes planner --planner-sweep"
    )


if __name__ == "__main__":
    main()
