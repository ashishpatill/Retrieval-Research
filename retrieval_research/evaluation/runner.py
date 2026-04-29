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


def _planner_static_comparison(metrics_by_mode: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    planner = metrics_by_mode.get("planner")
    if not planner:
        return {"available": False, "reason": "planner mode was not run"}

    baselines = {mode: values for mode, values in metrics_by_mode.items() if mode != "planner"}
    if not baselines:
        return {"available": False, "reason": "no static baseline modes were run"}

    baseline_keys = ("term_hit_rate", "page_hit_rate", "citation_support_rate", "answerable_rate", "mrr", "avg_confidence")
    baseline_avg = {
        key: sum(values[key] for values in baselines.values()) / len(baselines)
        for key in baseline_keys
    }
    delta = {key: planner[key] - baseline_avg[key] for key in baseline_keys}
    wins = [key for key, value in delta.items() if value > 0]
    losses = [key for key, value in delta.items() if value < 0]

    return {
        "available": True,
        "baseline_modes": sorted(baselines.keys()),
        "baseline_average": baseline_avg,
        "planner": {key: planner[key] for key in baseline_keys},
        "delta_vs_baseline_avg": delta,
        "wins": wins,
        "losses": losses,
        "summary": (
            f"Planner beats static average on {len(wins)}/{len(baseline_keys)} metrics."
            if wins
            else "Planner does not beat static average on any tracked metric."
        ),
    }


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
            answerable = bool(knowledge_card.get("answerable"))
            confidence = float(knowledge_card.get("confidence", 0.0))
            results.append(
                {
                    "query": case["query"],
                    "document_id": document_id,
                    "mode": mode,
                    "term_hit": term_hit,
                    "page_hit": page_hit,
                    "citation_supported": citation_supported,
                    "answerable": answerable,
                    "confidence": confidence,
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
            "answerable_rate": sum(1 for item in mode_results if item["answerable"]) / total,
            "avg_confidence": sum(item["confidence"] for item in mode_results) / total,
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
            "planner_vs_static": _planner_static_comparison(metrics_by_mode),
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
        "| Mode | Queries | Term hit rate | Page hit rate | Citation support | Answerable | Avg confidence | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in sorted(metrics["modes"]):
        mode_metrics = metrics["modes"][mode]
        lines.append(
            f"| {mode} | {mode_metrics['query_count']} | "
            f"{mode_metrics['term_hit_rate']:.3f} | {mode_metrics['page_hit_rate']:.3f} | "
            f"{mode_metrics['citation_support_rate']:.3f} | {mode_metrics['answerable_rate']:.3f} | "
            f"{mode_metrics['avg_confidence']:.3f} | {mode_metrics['mrr']:.3f} |"
        )
    lines.extend([
        "",
        "## Planner vs Static",
        "",
    ])
    comparison = metrics.get("planner_vs_static", {"available": False})
    if not comparison.get("available"):
        lines.append(f"- Not available: {comparison.get('reason', 'insufficient modes')}")
    else:
        lines.append(f"- Baselines: {', '.join(comparison['baseline_modes'])}")
        lines.append(f"- {comparison['summary']}")
        lines.extend([
            "",
            "| Metric | Planner | Static avg | Delta |",
            "|---|---:|---:|---:|",
        ])
        for metric in ("term_hit_rate", "page_hit_rate", "citation_support_rate", "answerable_rate", "mrr", "avg_confidence"):
            planner_value = comparison["planner"][metric]
            baseline_value = comparison["baseline_average"][metric]
            delta = comparison["delta_vs_baseline_avg"][metric]
            lines.append(f"| {metric} | {planner_value:.3f} | {baseline_value:.3f} | {delta:+.3f} |")

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
                f"- Answerable: {item['answerable']}",
                f"- Confidence: {item['confidence']:.3f}",
                f"- Reciprocal rank: {item['reciprocal_rank']:.3f}",
                f"- Top score: {item['top_score']:.3f}",
            ]
        )
    return "\n".join(lines) + "\n"
