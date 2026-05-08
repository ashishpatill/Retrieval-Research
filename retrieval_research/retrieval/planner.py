from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


PLANNER_MERGE_STRATEGIES = ("score_max", "route_vote")

_STEM_SUFFIXES = ("s", "es", "ies", "ing", "ed", "tion", "ings")

TABLE_TERMS = {
    "table", "tables", "tabular",
    "row", "rows",
    "column", "columns",
    "cell", "cells",
    "invoice", "invoices",
    "form", "forms",
    "total", "totals", "amount", "amounts",
    "spreadsheet", "spreadsheets",
    "ledger", "register", "financial",
    "metric", "metrics", "stat", "stats",
    "grid", "matrix",
}
VISUAL_TERMS = {
    "figure", "figures",
    "diagram", "diagrams",
    "chart", "charts",
    "plot", "plots",
    "image", "images", "imagery",
    "screenshot", "screenshots",
    "flowchart", "flowcharts",
    "visual", "visually", "visualization", "visualizations",
    "layout", "layouts",
    "page", "pages",
    "scan", "scans", "scanning",
    "handwriting",
    "graph", "graphs",
    "drawing", "drawings",
    "sketch", "sketches",
    "photo", "photos", "photograph", "photographs",
    "illustration", "illustrations",
    "map", "maps",
}
MULTIHOP_TERMS = {
    "compare", "comparison", "comparing",
    "contrast",
    "relationship", "relationships",
    "across",
    "between",
    "cross",
    "corpus",
    "documents",
    "multi",
    "summarize", "summarizes", "summary",
    "synthesis", "synthesize",
    "overview",
    "aggregate",
    "among",
}
GRAPH_TERMS = {
    "section", "sections",
    "reference", "references",
    "entity", "entities",
    "topic", "topics",
    "related",
    "neighbor", "neighbors", "neighborhood",
    "context", "contexts",
    "hierarchy", "hierarchical",
    "outline",
    "structure", "structures",
    "navigation",
}


def _normalize_terms(terms: set[str]) -> set[str]:
    normalized = set(terms)
    for term in terms:
        for suffix in _STEM_SUFFIXES:
            if term.endswith(suffix) and len(term) > len(suffix) + 2:
                stem = term[: -len(suffix)]
                normalized.add(stem)
                if suffix == "ies" and term.endswith("ies"):
                    normalized.add(stem + "y")
    return normalized


@dataclass
class QueryPlan:
    query_type: str
    routes: List[str]
    reason: str
    route_explanation: str
    route_settings: Dict[str, dict]
    merge_strategy: str = "score_max"

    def to_dict(self) -> dict:
        return {
            "query_type": self.query_type,
            "routes": self.routes,
            "reason": self.reason,
            "route_explanation": self.route_explanation,
            "route_settings": self.route_settings,
            "merge_strategy": self.merge_strategy,
        }


def _settings_for(query_type: str, routes: List[str]) -> Dict[str, dict]:
    base = {
        "bm25": {"top_k_factor": 2.0},
        "dense": {"top_k_factor": 2.0},
        "late": {"top_k_factor": 2.0, "scorer": "maxsim"},
        "visual": {"top_k_factor": 2.0},
        "graph": {"top_k_factor": 2.0, "expansion": "section_entity_reference_graph"},
        "hybrid": {"top_k_factor": 2.0, "fusion": "reciprocal_rank"},
    }
    settings = {route: dict(base.get(route, {"top_k_factor": 2.0})) for route in routes}
    if query_type == "multi_hop":
        for route in settings.values():
            route["top_k_factor"] = max(route.get("top_k_factor", 2.0), 3.0)
    elif query_type == "exact_lookup":
        settings["bm25"] = {"top_k_factor": 2.5}
    elif query_type == "visual":
        settings["visual"] = {"top_k_factor": 3.0}
    return settings


def _looks_like_identifier_query(query: str, terms: set[str]) -> bool:
    if re.search(r"\b[A-Z]{2,}[-_ ]?\d{2,}\b", query):
        return True
    identifier_hints = {"id", "invoice", "section", "figure", "table", "eq", "equation", "code", "ticket"}
    if not (terms & identifier_hints):
        return False
    for term in terms:
        if len(term) >= 4 and any(ch.isalpha() for ch in term) and any(ch.isdigit() for ch in term):
            return True
    return bool(re.search(r"\b\d{3,}\b", query))


def plan_query(query: str, merge_strategy: str = "score_max") -> QueryPlan:
    if merge_strategy not in PLANNER_MERGE_STRATEGIES:
        raise ValueError(f"Unsupported planner merge strategy: {merge_strategy}")
    normalized = query.lower()
    raw_terms = set(re.findall(r"[a-z0-9_]+", normalized))
    terms = raw_terms | _normalize_terms(raw_terms)

    if terms & VISUAL_TERMS:
        has_text_terms = bool(terms - VISUAL_TERMS - TABLE_TERMS - MULTIHOP_TERMS - GRAPH_TERMS)
        if has_text_terms:
            routes = ["visual", "hybrid"]
        else:
            routes = ["visual"]
        return QueryPlan(
            query_type="visual",
            routes=routes,
            reason="visual/layout terms detected",
            route_explanation="Detected visual/layout terms, prioritizing visual retrieval with hybrid fallback."
            if has_text_terms
            else "Detected visual-only terms, using visual retrieval.",
            route_settings=_settings_for("visual", routes),
            merge_strategy=merge_strategy,
        )

    if terms & TABLE_TERMS:
        if terms & MULTIHOP_TERMS:
            routes = ["hybrid", "late", "bm25"]
            return QueryPlan(
                query_type="multi_hop",
                routes=routes,
                reason="table/form terms with multi-hop intent",
                route_explanation="Detected table/form terms with multi-hop/comparison intent, routing to late interaction and hybrid.",
                route_settings=_settings_for("multi_hop", routes),
                merge_strategy=merge_strategy,
            )
        routes = ["late", "hybrid"]
        return QueryPlan(
            query_type="table_or_form",
            routes=routes,
            reason="table/form terms detected",
            route_explanation="Detected table/form terms, prioritizing late interaction with hybrid fallback.",
            route_settings=_settings_for("table_or_form", routes),
            merge_strategy=merge_strategy,
        )

    if terms & GRAPH_TERMS:
        if terms & MULTIHOP_TERMS:
            routes = ["graph", "hybrid"]
            return QueryPlan(
                query_type="multi_hop",
                routes=routes,
                reason="graph/section terms with multi-hop intent",
                route_explanation="Detected graph/section terms with multi-hop intent, routing to graph traversal and hybrid.",
                route_settings=_settings_for("multi_hop", routes),
                merge_strategy=merge_strategy,
            )
        routes = ["graph", "hybrid"]
        return QueryPlan(
            query_type="graph_nav",
            routes=routes,
            reason="graph/section terms detected",
            route_explanation="Detected graph/section terms, routing to graph retrieval with hybrid fallback.",
            route_settings=_settings_for("graph_nav", routes),
            merge_strategy=merge_strategy,
        )

    if terms & MULTIHOP_TERMS:
        routes = ["hybrid", "dense"]
        return QueryPlan(
            query_type="multi_hop",
            routes=routes,
            reason="multi-hop terms detected",
            route_explanation="Detected multi-hop/comparison terms, routing to hybrid and dense retrieval.",
            route_settings=_settings_for("multi_hop", routes),
            merge_strategy=merge_strategy,
        )

    if _looks_like_identifier_query(query, terms):
        routes = ["bm25"]
        return QueryPlan(
            query_type="exact_lookup",
            routes=routes,
            reason="identifier/code pattern detected",
            route_explanation="Detected identifier or code-like pattern, routing directly to BM25.",
            route_settings=_settings_for("exact_lookup", routes),
            merge_strategy=merge_strategy,
        )

    return QueryPlan(
        query_type="semantic",
        routes=["dense", "bm25"],
        reason="default semantic routing",
        route_explanation="No specific visual/table/graph/identifier terms detected; using dense + BM25 hybrid.",
        route_settings=_settings_for("semantic", ["dense", "bm25"]),
        merge_strategy=merge_strategy,
    )
