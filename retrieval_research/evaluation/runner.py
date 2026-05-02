from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from retrieval_research.evidence import build_knowledge_card
from retrieval_research.retrieval import (
    DEFAULT_PLANNER_RERANK,
    DEFAULT_RERANK_OVERLAP_WEIGHT,
    DEFAULT_ROUTE_VOTE_BONUS,
    PLANNER_MERGE_STRATEGIES,
    RETRIEVAL_MODES,
    search_corpus,
    search_document,
)
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


def _graph_diagnostics_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    graph_steps = [
        step
        for item in results
        for step in item.get("steps", [])
        if step.get("path") in {"graph", "graph_corpus"} and step.get("diagnostics")
    ]
    if not graph_steps:
        return {"available": False, "reason": "graph mode was not run or did not emit diagnostics"}

    relation_counts: Dict[str, int] = {}
    seed_total = 0
    expanded_total = 0
    edge_total = 0
    node_total = 0
    document_counts = []
    for step in graph_steps:
        diagnostics = step["diagnostics"]
        seed_total += int(diagnostics.get("seed_count", 0))
        expanded_total += int(diagnostics.get("expanded_count", 0))
        edge_total += int(diagnostics.get("edge_count", 0))
        node_total += int(diagnostics.get("node_count", 0))
        if diagnostics.get("document_count") is not None:
            document_counts.append(int(diagnostics["document_count"]))
        for relation, count in diagnostics.get("expanded_relation_counts", diagnostics.get("relation_counts", {})).items():
            relation_counts[relation] = relation_counts.get(relation, 0) + int(count)

    total = len(graph_steps)
    return {
        "available": True,
        "step_count": total,
        "avg_seed_count": seed_total / total,
        "avg_expanded_count": expanded_total / total,
        "avg_node_count": node_total / total,
        "avg_edge_count": edge_total / total,
        "max_document_count": max(document_counts) if document_counts else 1,
        "relation_counts": dict(sorted(relation_counts.items())),
    }


def _visual_diagnostics_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    visual_steps = [
        step
        for item in results
        for step in item.get("steps", [])
        if str(step.get("path", "")).startswith("visual")
    ]
    visual_hits = [
        hit
        for item in results
        for hit in item.get("hits", [])
        if str(hit.get("retrieval_path", "")).startswith("visual")
    ]
    planner_rows = [item for item in results if item.get("mode") == "planner"]
    planner_visual_rows = []
    for item in planner_rows:
        contributed = any(
            "visual" in source_path
            for hit in item.get("hits", [])
            for source_path in hit.get("metadata", {}).get("source_paths", [])
        )
        if contributed:
            planner_visual_rows.append(item)

    if not visual_steps and not visual_hits and not planner_rows:
        return {"available": False, "reason": "visual retrieval was not run"}

    planner_total = len(planner_rows)
    planner_visual_total = len(planner_visual_rows)
    return {
        "available": True,
        "visual_step_count": len(visual_steps),
        "visual_hit_count": len(visual_hits),
        "planner_query_count": planner_total,
        "planner_visual_contribution_count": planner_visual_total,
        "planner_visual_contribution_rate": (planner_visual_total / planner_total) if planner_total else 0.0,
    }


def _expected_values(manifest: Dict[str, Any], cases: List[Dict[str, Any]], key: str) -> List[str]:
    values = list(manifest.get(key, []))
    for case in cases:
        values.extend(case.get(key, []))
    return sorted({str(value) for value in values})


def _expected_values_by_tier(manifest: Dict[str, Any], cases: List[Dict[str, Any]], key: str) -> Dict[str, List[str]]:
    values: Dict[str, List[str]] = {}
    tier_key = f"{key}_by_tier"

    def _merge(payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        for tier, tier_values in payload.items():
            if not isinstance(tier_values, list):
                continue
            bucket = values.setdefault(str(tier), [])
            bucket.extend(str(value) for value in tier_values)

    _merge(manifest.get(tier_key))
    for case in cases:
        _merge(case.get(tier_key))
    return {tier: sorted(set(items)) for tier, items in values.items()}


def _document_quality_tiers(
    store: ArtifactStore,
    manifest: Dict[str, Any],
    cases: List[Dict[str, Any]],
    document_ids: set[str],
) -> Dict[str, str]:
    tiers: Dict[str, str] = {}

    for doc_id, tier in (manifest.get("document_quality_tiers") or {}).items():
        tiers[str(doc_id)] = str(tier)
    for case in cases:
        for doc_id, tier in (case.get("document_quality_tiers") or {}).items():
            tiers[str(doc_id)] = str(tier)

    for document_id in document_ids:
        if document_id in tiers:
            continue
        try:
            document = store.load_document(document_id)
            metadata = document.metadata or {}
            tier = metadata.get("source_quality_tier") or metadata.get("quality_tier") or metadata.get("ocr_quality_tier")
            if tier:
                tiers[document_id] = str(tier)
        except FileNotFoundError:
            continue

    for document_id in document_ids:
        tiers.setdefault(document_id, "unlabeled")
    return tiers


def _graph_extraction_summary(
    store: ArtifactStore,
    manifest: Dict[str, Any],
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    document_ids = set(manifest.get("document_ids", []))
    if manifest.get("document_id"):
        document_ids.add(str(manifest["document_id"]))
    for case in cases:
        document_ids.update(str(value) for value in case.get("document_ids", []))
        if case.get("document_id"):
            document_ids.add(str(case["document_id"]))

    if not document_ids:
        return {"available": False, "reason": "manifest did not identify documents for graph extraction summary"}

    graphs = []
    missing = []
    for document_id in sorted(document_ids):
        try:
            graphs.append((document_id, store.load_knowledge_graph(document_id)))
        except FileNotFoundError:
            missing.append(document_id)

    if not graphs:
        return {"available": False, "reason": "no knowledge_graph.json artifacts found", "missing_document_ids": missing}

    relation_counts: Dict[str, int] = {}
    entity_names = set()
    reference_names = set()
    section_names = set()
    documents = []
    quality_tiers = _document_quality_tiers(store, manifest, cases, document_ids)
    tier_totals: Dict[str, Dict[str, int]] = {}
    tier_relations: Dict[str, Dict[str, int]] = {}
    tier_entities: Dict[str, set[str]] = {}
    tier_references: Dict[str, set[str]] = {}
    tier_sections: Dict[str, set[str]] = {}
    tier_documents: Dict[str, List[str]] = {}
    totals = {
        "node_count": 0,
        "edge_count": 0,
        "section_count": 0,
        "entity_count": 0,
        "reference_count": 0,
    }
    for document_id, graph in graphs:
        stats = graph.get("stats", {})
        tier = quality_tiers.get(document_id, "unlabeled")
        tier_totals.setdefault(
            tier,
            {
                "node_count": 0,
                "edge_count": 0,
                "section_count": 0,
                "entity_count": 0,
                "reference_count": 0,
            },
        )
        tier_relations.setdefault(tier, {})
        tier_entities.setdefault(tier, set())
        tier_references.setdefault(tier, set())
        tier_sections.setdefault(tier, set())
        tier_documents.setdefault(tier, []).append(document_id)

        per_doc_stats = {key: int(stats.get(key, 0)) for key in totals}
        for key in totals:
            totals[key] += per_doc_stats[key]
            tier_totals[tier][key] += per_doc_stats[key]
        for relation, count in stats.get("relation_counts", {}).items():
            relation_counts[relation] = relation_counts.get(relation, 0) + int(count)
            tier_relations[tier][relation] = tier_relations[tier].get(relation, 0) + int(count)
        entity_names.update(str(item.get("name", "")).lower() for item in graph.get("entities", []) if item.get("name"))
        reference_names.update(str(item.get("reference", "")).lower() for item in graph.get("references", []) if item.get("reference"))
        section_names.update(str(item.get("name", "")).lower() for item in graph.get("sections", []) if item.get("name"))
        tier_entities[tier].update(str(item.get("name", "")).lower() for item in graph.get("entities", []) if item.get("name"))
        tier_references[tier].update(
            str(item.get("reference", "")).lower() for item in graph.get("references", []) if item.get("reference")
        )
        tier_sections[tier].update(str(item.get("name", "")).lower() for item in graph.get("sections", []) if item.get("name"))
        documents.append({"document_id": document_id, "quality_tier": tier, **per_doc_stats})

    expected_entities = _expected_values(manifest, cases, "expected_entities")
    expected_references = _expected_values(manifest, cases, "expected_references")
    expected_sections = _expected_values(manifest, cases, "expected_sections")
    expected_entities_by_tier = _expected_values_by_tier(manifest, cases, "expected_entities")
    expected_references_by_tier = _expected_values_by_tier(manifest, cases, "expected_references")
    expected_sections_by_tier = _expected_values_by_tier(manifest, cases, "expected_sections")

    def _recall(expected: List[str], observed: set[str]) -> Dict[str, Any]:
        if not expected:
            return {"available": False, "reason": "no expected values supplied"}
        hits = [value for value in expected if value.lower() in observed]
        return {
            "available": True,
            "expected_count": len(expected),
            "hit_count": len(hits),
            "recall": len(hits) / len(expected),
            "misses": [value for value in expected if value not in hits],
        }

    document_count = len(graphs)
    quality_tier_summary = []
    for tier in sorted(tier_totals):
        tier_doc_count = max(1, len(tier_documents.get(tier, [])))
        quality_tier_summary.append(
            {
                "quality_tier": tier,
                "document_count": len(tier_documents.get(tier, [])),
                "document_ids": sorted(tier_documents.get(tier, [])),
                "totals": tier_totals[tier],
                "averages": {key: tier_totals[tier][key] / tier_doc_count for key in tier_totals[tier]},
                "relation_counts": dict(sorted(tier_relations.get(tier, {}).items())),
                "expected_recall": {
                    "entities": _recall(expected_entities_by_tier.get(tier, []), tier_entities.get(tier, set())),
                    "references": _recall(expected_references_by_tier.get(tier, []), tier_references.get(tier, set())),
                    "sections": _recall(expected_sections_by_tier.get(tier, []), tier_sections.get(tier, set())),
                },
            }
        )

    return {
        "available": True,
        "document_count": document_count,
        "missing_document_ids": missing,
        "totals": totals,
        "averages": {key: totals[key] / document_count for key in totals},
        "relation_counts": dict(sorted(relation_counts.items())),
        "expected_recall": {
            "entities": _recall(expected_entities, entity_names),
            "references": _recall(expected_references, reference_names),
            "sections": _recall(expected_sections, section_names),
        },
        "quality_tiers": quality_tier_summary,
        "documents": documents,
    }


def _planner_sweep_variants(
    value: Any,
    route_vote_bonus: float,
    rerank_overlap_weight: float,
) -> List[Dict[str, Any]]:
    if not value:
        return []
    if value is True:
        return [
            {
                "name": f"{strategy}{'_rerank' if rerank else ''}",
                "merge_strategy": strategy,
                "rerank": rerank,
                "route_vote_bonus": route_vote_bonus,
                "rerank_overlap_weight": rerank_overlap_weight,
            }
            for strategy in PLANNER_MERGE_STRATEGIES
            for rerank in (False, True)
        ]
    variants = []
    for idx, item in enumerate(value if isinstance(value, list) else []):
        strategy = str(item.get("merge_strategy", "score_max"))
        rerank = bool(item.get("rerank", False))
        if strategy not in PLANNER_MERGE_STRATEGIES:
            raise ValueError(f"Unsupported planner merge strategy: {strategy}")
        variants.append(
            {
                "name": str(item.get("name") or f"{strategy}{'_rerank' if rerank else ''}_{idx + 1}"),
                "merge_strategy": strategy,
                "rerank": rerank,
                "route_vote_bonus": float(item.get("route_vote_bonus", route_vote_bonus)),
                "rerank_overlap_weight": float(item.get("rerank_overlap_weight", rerank_overlap_weight)),
            }
        )
    return variants


def _run_planner_case(
    store: ArtifactStore,
    case: Dict[str, Any],
    manifest: Dict[str, Any],
    top_k: int,
    merge_strategy: str,
    rerank: bool,
    route_vote_bonus: float,
    rerank_overlap_weight: float,
) -> Dict[str, Any]:
    document_id = case.get("document_id") or manifest.get("document_id")
    document_ids = case.get("document_ids") or manifest.get("document_ids")
    if document_id:
        document_ids = [document_id]
    if not document_ids:
        raise ValueError("Planner sweep cases need document_id/document_ids, or manifest top-level document_id/document_ids.")

    if len(document_ids) == 1:
        evidence, steps = search_document(
            store,
            document_ids[0],
            case["query"],
            mode="planner",
            top_k=top_k,
            planner_merge_strategy=merge_strategy,
            planner_rerank=rerank,
            planner_route_vote_bonus=route_vote_bonus,
            planner_rerank_overlap_weight=rerank_overlap_weight,
        )
    else:
        evidence, steps = search_corpus(
            store,
            document_ids,
            case["query"],
            mode="planner",
            top_k=top_k,
            planner_merge_strategy=merge_strategy,
            planner_rerank=rerank,
            planner_route_vote_bonus=route_vote_bonus,
            planner_rerank_overlap_weight=rerank_overlap_weight,
        )
    knowledge_card = build_knowledge_card(case["query"], evidence).to_dict()
    expected_terms = case.get("expected_terms", [])
    expected_pages = case.get("expected_pages", [])
    return {
        "query": case["query"],
        "document_id": document_ids[0] if len(document_ids) == 1 else None,
        "document_ids": document_ids,
        "term_hit": _contains_expected_terms(evidence, expected_terms),
        "page_hit": _hits_expected_page(evidence, expected_pages),
        "citation_supported": _has_supported_citations(knowledge_card),
        "answerable": bool(knowledge_card.get("answerable")),
        "confidence": float(knowledge_card.get("confidence", 0.0)),
        "reciprocal_rank": _reciprocal_rank(evidence, expected_terms, expected_pages),
        "top_score": evidence[0].score if evidence else 0.0,
        "steps": steps,
        "hits": [item.to_dict() for item in evidence],
    }


def _planner_sweep_summary(
    store: ArtifactStore,
    manifest: Dict[str, Any],
    cases: List[Dict[str, Any]],
    top_k: int,
    variants: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not variants:
        return {"available": False, "reason": "planner sweep was not requested"}

    variant_reports = []
    for variant in variants:
        rows = [
            _run_planner_case(
                store,
                case,
                manifest,
                top_k,
                merge_strategy=variant["merge_strategy"],
                rerank=variant["rerank"],
                route_vote_bonus=float(variant["route_vote_bonus"]),
                rerank_overlap_weight=float(variant["rerank_overlap_weight"]),
            )
            for case in cases
        ]
        total = len(rows) or 1
        metrics = {
            "term_hit_rate": sum(1 for row in rows if row["term_hit"]) / total,
            "page_hit_rate": sum(1 for row in rows if row["page_hit"]) / total,
            "citation_support_rate": sum(1 for row in rows if row["citation_supported"]) / total,
            "answerable_rate": sum(1 for row in rows if row["answerable"]) / total,
            "avg_confidence": sum(row["confidence"] for row in rows) / total,
            "mrr": sum(row["reciprocal_rank"] for row in rows) / total,
            "avg_top_score": sum(row["top_score"] for row in rows) / total,
            "query_count": len(rows),
        }
        variant_reports.append({**variant, "metrics": metrics, "results": rows})

    best_by_mrr = max(variant_reports, key=lambda item: item["metrics"]["mrr"])
    best_by_confidence = max(variant_reports, key=lambda item: item["metrics"]["avg_confidence"])
    return {
        "available": True,
        "variants": variant_reports,
        "best_by_mrr": best_by_mrr["name"],
        "best_by_confidence": best_by_confidence["name"],
    }


def run_eval(
    manifest_path: str,
    store: Optional[ArtifactStore] = None,
    top_k: int = 5,
    modes: Optional[List[str]] = None,
    planner_merge_strategy: str = "score_max",
    planner_rerank: bool = DEFAULT_PLANNER_RERANK,
    planner_route_vote_bonus: float = DEFAULT_ROUTE_VOTE_BONUS,
    planner_rerank_overlap_weight: float = DEFAULT_RERANK_OVERLAP_WEIGHT,
    planner_sweep: Any = False,
) -> Dict[str, Any]:
    store = store or ArtifactStore()
    modes = modes or list(RETRIEVAL_MODES)
    manifest = _load_manifest(manifest_path)
    cases = manifest.get("queries", [])
    results = []
    planner_merge_strategy = str(manifest.get("planner_merge_strategy", planner_merge_strategy))
    planner_rerank = bool(manifest.get("planner_rerank", planner_rerank))
    planner_route_vote_bonus = float(manifest.get("planner_route_vote_bonus", planner_route_vote_bonus))
    planner_rerank_overlap_weight = float(manifest.get("planner_rerank_overlap_weight", planner_rerank_overlap_weight))
    planner_sweep_variants = _planner_sweep_variants(
        manifest.get("planner_sweep", planner_sweep),
        planner_route_vote_bonus,
        planner_rerank_overlap_weight,
    )

    for mode in modes:
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
    if planner_merge_strategy not in PLANNER_MERGE_STRATEGIES:
        raise ValueError(f"Unsupported planner merge strategy: {planner_merge_strategy}")

    for case in cases:
        document_id = case.get("document_id") or manifest.get("document_id")
        document_ids = case.get("document_ids") or manifest.get("document_ids")
        if document_id:
            document_ids = [document_id]
        if not document_ids:
            raise ValueError(
                "Each eval case needs document_id/document_ids, or manifest needs top-level document_id/document_ids."
            )

        for mode in modes:
            case_merge_strategy = str(case.get("planner_merge_strategy", planner_merge_strategy))
            case_rerank = bool(case.get("planner_rerank", planner_rerank))
            case_route_vote_bonus = float(case.get("planner_route_vote_bonus", planner_route_vote_bonus))
            case_rerank_overlap_weight = float(case.get("planner_rerank_overlap_weight", planner_rerank_overlap_weight))
            if len(document_ids) == 1:
                evidence, steps = search_document(
                    store,
                    document_ids[0],
                    case["query"],
                    mode=mode,
                    top_k=top_k,
                    planner_merge_strategy=case_merge_strategy,
                    planner_rerank=case_rerank,
                    planner_route_vote_bonus=case_route_vote_bonus,
                    planner_rerank_overlap_weight=case_rerank_overlap_weight,
                )
            else:
                evidence, steps = search_corpus(
                    store,
                    document_ids,
                    case["query"],
                    mode=mode,
                    top_k=top_k,
                    planner_merge_strategy=case_merge_strategy,
                    planner_rerank=case_rerank,
                    planner_route_vote_bonus=case_route_vote_bonus,
                    planner_rerank_overlap_weight=case_rerank_overlap_weight,
                )
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
                    "document_id": document_ids[0] if len(document_ids) == 1 else None,
                    "document_ids": document_ids,
                    "mode": mode,
                    "planner_merge_strategy": case_merge_strategy if mode == "planner" else None,
                    "planner_rerank": case_rerank if mode == "planner" else None,
                    "planner_route_vote_bonus": case_route_vote_bonus if mode == "planner" else None,
                    "planner_rerank_overlap_weight": case_rerank_overlap_weight if mode == "planner" else None,
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
    for mode in sorted(modes):
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
        "planner": {
            "merge_strategy": planner_merge_strategy,
            "rerank": planner_rerank,
            "route_vote_bonus": planner_route_vote_bonus,
            "rerank_overlap_weight": planner_rerank_overlap_weight,
            "merge_strategies": list(PLANNER_MERGE_STRATEGIES),
        },
        "metrics": {
            "query_count": len(results),
            "modes": metrics_by_mode,
            "planner_vs_static": _planner_static_comparison(metrics_by_mode),
            "visual_diagnostics": _visual_diagnostics_summary(results),
            "graph_diagnostics": _graph_diagnostics_summary(results),
            "graph_extraction": _graph_extraction_summary(store, manifest, cases),
            "planner_sweep": _planner_sweep_summary(store, manifest, cases, top_k, planner_sweep_variants),
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
        f"- Planner merge strategy: {report.get('planner', {}).get('merge_strategy', 'score_max')}",
        f"- Planner rerank: {report.get('planner', {}).get('rerank', DEFAULT_PLANNER_RERANK)}",
        f"- Planner route vote bonus: {report.get('planner', {}).get('route_vote_bonus', DEFAULT_ROUTE_VOTE_BONUS):.3f}",
        f"- Planner rerank overlap weight: {report.get('planner', {}).get('rerank_overlap_weight', DEFAULT_RERANK_OVERLAP_WEIGHT):.3f}",
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

    planner_sweep = metrics.get("planner_sweep", {"available": False})
    lines.extend([
        "",
        "## Planner Sweep",
        "",
    ])
    if not planner_sweep.get("available"):
        lines.append(f"- Not available: {planner_sweep.get('reason', 'planner sweep unavailable')}")
    else:
        lines.append(f"- Best by MRR: {planner_sweep['best_by_mrr']}")
        lines.append(f"- Best by confidence: {planner_sweep['best_by_confidence']}")
        lines.extend([
            "",
            "| Variant | Strategy | Rerank | Vote bonus | Overlap weight | MRR | Avg confidence | Term hit | Page hit |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for variant in planner_sweep["variants"]:
            variant_metrics = variant["metrics"]
            lines.append(
                f"| {variant['name']} | {variant['merge_strategy']} | {variant['rerank']} | "
                f"{float(variant.get('route_vote_bonus', DEFAULT_ROUTE_VOTE_BONUS)):.3f} | "
                f"{float(variant.get('rerank_overlap_weight', DEFAULT_RERANK_OVERLAP_WEIGHT)):.3f} | "
                f"{variant_metrics['mrr']:.3f} | {variant_metrics['avg_confidence']:.3f} | "
                f"{variant_metrics['term_hit_rate']:.3f} | {variant_metrics['page_hit_rate']:.3f} |"
            )

    visual_diagnostics = metrics.get("visual_diagnostics", {"available": False})
    lines.extend([
        "",
        "## Visual Diagnostics",
        "",
    ])
    if not visual_diagnostics.get("available"):
        lines.append(f"- Not available: {visual_diagnostics.get('reason', 'visual diagnostics unavailable')}")
    else:
        lines.append(f"- Visual steps: {visual_diagnostics['visual_step_count']}")
        lines.append(f"- Visual hits: {visual_diagnostics['visual_hit_count']}")
        lines.append(f"- Planner queries: {visual_diagnostics['planner_query_count']}")
        lines.append(
            f"- Planner rows with visual contribution: {visual_diagnostics['planner_visual_contribution_count']} "
            f"({visual_diagnostics['planner_visual_contribution_rate']:.3f})"
        )

    graph_diagnostics = metrics.get("graph_diagnostics", {"available": False})
    lines.extend([
        "",
        "## Graph Diagnostics",
        "",
    ])
    if not graph_diagnostics.get("available"):
        lines.append(f"- Not available: {graph_diagnostics.get('reason', 'graph diagnostics unavailable')}")
    else:
        lines.append(f"- Graph steps: {graph_diagnostics['step_count']}")
        lines.append(f"- Avg seeds: {graph_diagnostics['avg_seed_count']:.3f}")
        lines.append(f"- Avg expanded nodes: {graph_diagnostics['avg_expanded_count']:.3f}")
        lines.append(f"- Max document count: {graph_diagnostics['max_document_count']}")
        if graph_diagnostics.get("relation_counts"):
            relation_summary = ", ".join(
                f"{relation}={count}" for relation, count in graph_diagnostics["relation_counts"].items()
            )
            lines.append(f"- Expanded relations: {relation_summary}")

    graph_extraction = metrics.get("graph_extraction", {"available": False})
    lines.extend([
        "",
        "## Graph Extraction",
        "",
    ])
    if not graph_extraction.get("available"):
        lines.append(f"- Not available: {graph_extraction.get('reason', 'graph extraction summary unavailable')}")
    else:
        totals = graph_extraction["totals"]
        lines.append(f"- Documents with graph artifacts: {graph_extraction['document_count']}")
        lines.append(
            f"- Totals: sections={totals['section_count']}, entities={totals['entity_count']}, "
            f"references={totals['reference_count']}, edges={totals['edge_count']}"
        )
        for label, recall in graph_extraction.get("expected_recall", {}).items():
            if recall.get("available"):
                lines.append(
                    f"- Expected {label} recall: {recall['hit_count']}/{recall['expected_count']} "
                    f"({recall['recall']:.3f})"
                )
        for tier in graph_extraction.get("quality_tiers", []):
            lines.append(
                f"- Tier `{tier['quality_tier']}`: docs={tier['document_count']}, "
                f"entities={tier['totals']['entity_count']}, references={tier['totals']['reference_count']}"
            )
            for label, recall in tier.get("expected_recall", {}).items():
                if recall.get("available"):
                    lines.append(
                        f"  - Expected {label} recall: {recall['hit_count']}/{recall['expected_count']} "
                        f"({recall['recall']:.3f})"
                    )
        if graph_extraction.get("missing_document_ids"):
            lines.append(f"- Missing graph artifacts: {', '.join(graph_extraction['missing_document_ids'])}")

    lines.extend([
        "",
        "## Queries",
    ])
    for item in sorted(report["results"], key=lambda row: (row["query"], row["mode"])):
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
