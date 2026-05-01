from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


PLANNER_MERGE_STRATEGIES = ("score_max", "route_vote")
TABLE_TERMS = {"table", "row", "column", "cell", "invoice", "form", "total", "amount", "spreadsheet"}
VISUAL_TERMS = {
    "figure",
    "diagram",
    "chart",
    "plot",
    "image",
    "screenshot",
    "flowchart",
    "visual",
    "layout",
    "page",
    "scan",
    "handwriting",
}
MULTIHOP_TERMS = {
    "compare",
    "contrast",
    "relationship",
    "across",
    "between",
    "cross",
    "corpus",
    "documents",
    "multi",
    "summarize",
    "synthesis",
}
GRAPH_TERMS = {"section", "reference", "entity", "topic", "related", "neighbor", "context"}


@dataclass
class QueryPlan:
    query_type: str
    routes: List[str]
    reason: str
    route_settings: Dict[str, dict]
    merge_strategy: str = "score_max"

    def to_dict(self) -> dict:
        return {
            "query_type": self.query_type,
            "routes": self.routes,
            "reason": self.reason,
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


def plan_query(query: str, merge_strategy: str = "score_max") -> QueryPlan:
    if merge_strategy not in PLANNER_MERGE_STRATEGIES:
        raise ValueError(f"Unsupported planner merge strategy: {merge_strategy}")
    normalized = query.lower()
    terms = set(re.findall(r"[a-z0-9_]+", normalized))

    if terms & VISUAL_TERMS:
        routes = ["visual", "hybrid"]
        return QueryPlan(
            query_type="visual",
            routes=routes,
            reason="visual/layout terms detected",
            route_settings=_settings_for("visual", routes),
            merge_strategy=merge_strategy,
        )
    if terms & TABLE_TERMS:
        routes = ["bm25", "late", "hybrid"]
        return QueryPlan(
            query_type="table_or_form",
            routes=routes,
            reason="table/form terms detected",
            route_settings=_settings_for("table_or_form", routes),
            merge_strategy=merge_strategy,
        )
    if terms & (MULTIHOP_TERMS | GRAPH_TERMS):
        routes = ["hybrid", "dense", "late", "graph"]
        return QueryPlan(
            query_type="multi_hop" if terms & MULTIHOP_TERMS else "graph_expansion",
            routes=routes,
            reason="synthesis, graph, or neighborhood terms detected",
            route_settings=_settings_for("multi_hop", routes),
            merge_strategy=merge_strategy,
        )
    if re.search(r"\b[A-Z]{2,}[-_ ]?\d+\b", query) or re.search(r"\d", query):
        routes = ["bm25", "late", "hybrid"]
        return QueryPlan(
            query_type="exact_lookup",
            routes=routes,
            reason="identifier or numeric lookup detected",
            route_settings=_settings_for("exact_lookup", routes),
            merge_strategy=merge_strategy,
        )
    routes = ["hybrid"]
    return QueryPlan(
        query_type="semantic",
        routes=routes,
        reason="default semantic retrieval route",
        route_settings=_settings_for("semantic", routes),
        merge_strategy=merge_strategy,
    )
