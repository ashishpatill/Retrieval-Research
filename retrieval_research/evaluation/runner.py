from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from retrieval_research.evidence import build_knowledge_card
from retrieval_research.retrieval import RETRIEVAL_MODES, search_document
from retrieval_research.schema import Evidence
from retrieval_research.storage import ArtifactStore


def _contains_expected_terms(evidence: List[Evidence], expected_terms: List[str]) -> bool:
    if not expected_terms:
        return False
    haystack = " ".join(item.text.lower() for item in evidence)
    return all(term.lower() in haystack for term in expected_terms)


def _hits_expected_page(evidence: List[Evidence], expected_pages: List[int]) -> bool:
    if not expected_pages:
        return False
    hit_pages = {page for item in evidence for page in item.page_numbers}
    return any(page in hit_pages for page in expected_pages)


def _reciprocal_rank(evidence: List[Evidence], expected_terms: List[str], expected_pages: List[int]) -> float:
    for idx, item in enumerate(evidence, 1):
        term_hit = _contains_expected_terms([item], expected_terms) if expected_terms else False
        page_hit = _hits_expected_page([item], expected_pages) if expected_pages else False
        if term_hit or page_hit:
            return 1.0 / idx
    return 0.0


def _has_supported_citations(card: Dict[str, Any]) -> bool:
    if not card.get("answerable"):
        return False
    citation_ids = {citation["id"] for citation in card.get("citations", [])}
    if not citation_ids:
        return False
    return all(
        bool(claim.get("citation_ids")) and set(claim.get("citation_ids")) <= citation_ids
        for claim in card.get("claims", [])
    )


def _load_manifest(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_eval(
    manifest_path: str,
    store: Optional[ArtifactStore] = None,
    top_k: int = 5,
    modes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    store = store or ArtifactStore()
    modes = modes or list(RETRIEVAL_MODES)
    manifest = _load_manifest(manifest_path)
    cases = manifest.get("queries", [])
    results = []

    for mode in modes:
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"Unsupported retrieval mode: {mode}")

    for case in cases:
        document_id = case.get("document_id") or manifest.get("document_id")
        if not document_id:
            raise ValueError("Each eval case needs document_id, or manifest needs a top-level document_id.")

        for mode in modes:
            evidence, steps = search_document(store, document_id, case["query"], mode=mode, top_k=top_k)
            knowledge_card = build_knowledge_card(case["query"], evidence).to_dict()
            expected_terms = case.get("expected_terms", [])
            expected_pages = case.get("expected_pages", [])
            term_hit = _contains_expected_terms(evidence, expected_terms)
            page_hit = _hits_expected_page(evidence, expected_pages)
            rr = _reciprocal_rank(evidence, expected_terms, expected_pages)
            citation_supported = _has_supported_citations(knowledge_card)
            results.append(
                {
                    "query": case["query"],
                    "document_id": document_id,
                    "mode": mode,
                    "term_hit": term_hit,
                    "page_hit": page_hit,
                    "citation_supported": citation_supported,
                    "reciprocal_rank": rr,
                    "top_score": evidence[0].score if evidence else 0.0,
                    "knowledge_card": knowledge_card,
                    "steps": steps,
                    "hits": [item.to_dict() for item in evidence],
                }
            )

    metrics_by_mode = {}
    for mode in modes:
        mode_results = [item for item in results if item["mode"] == mode]
        total = len(mode_results) or 1
        metrics_by_mode[mode] = {
            "term_hit_rate": sum(1 for item in mode_results if item["term_hit"]) / total,
            "page_hit_rate": sum(1 for item in mode_results if item["page_hit"]) / total,
            "citation_support_rate": sum(1 for item in mode_results if item["citation_supported"]) / total,
            "mrr": sum(item["reciprocal_rank"] for item in mode_results) / total,
            "query_count": len(mode_results),
        }

    report = {
        "manifest": manifest_path,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "top_k": top_k,
        "metrics": {
            "query_count": len(results),
            "modes": metrics_by_mode,
        },
        "results": results,
    }
    return report


def report_to_markdown(report: Dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Evaluation Report",
        "",
        f"- Result rows: {metrics['query_count']}",
        "",
        "## Mode Metrics",
        "",
        "| Mode | Queries | Term hit rate | Page hit rate | Citation support | MRR |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, mode_metrics in metrics["modes"].items():
        lines.append(
            f"| {mode} | {mode_metrics['query_count']} | "
            f"{mode_metrics['term_hit_rate']:.3f} | {mode_metrics['page_hit_rate']:.3f} | "
            f"{mode_metrics['citation_support_rate']:.3f} | {mode_metrics['mrr']:.3f} |"
        )
    lines.extend([
        "",
        "## Queries",
    ])
    for item in report["results"]:
        lines.extend(
            [
                "",
                f"### {item['query']} ({item['mode']})",
                "",
                f"- Term hit: {item['term_hit']}",
                f"- Page hit: {item['page_hit']}",
                f"- Citation supported: {item['citation_supported']}",
                f"- Reciprocal rank: {item['reciprocal_rank']:.3f}",
                f"- Top score: {item['top_score']:.3f}",
            ]
        )
    return "\n".join(lines) + "\n"
