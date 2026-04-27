from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


TABLE_TERMS = {"table", "row", "column", "cell", "invoice", "form", "total", "amount"}
VISUAL_TERMS = {"figure", "diagram", "chart", "image", "visual", "layout", "page", "scan", "handwriting"}
MULTIHOP_TERMS = {"compare", "contrast", "relationship", "across", "between", "summarize", "synthesis"}


@dataclass
class QueryPlan:
    query_type: str
    routes: List[str]
    reason: str

    def to_dict(self) -> dict:
        return {"query_type": self.query_type, "routes": self.routes, "reason": self.reason}


def plan_query(query: str) -> QueryPlan:
    normalized = query.lower()
    terms = set(re.findall(r"[a-z0-9_]+", normalized))

    if terms & VISUAL_TERMS:
        return QueryPlan(
            query_type="visual",
            routes=["visual", "hybrid"],
            reason="visual/layout terms detected",
        )
    if terms & TABLE_TERMS:
        return QueryPlan(
            query_type="table_or_form",
            routes=["bm25", "hybrid"],
            reason="table/form terms detected",
        )
    if terms & MULTIHOP_TERMS:
        return QueryPlan(
            query_type="multi_hop",
            routes=["hybrid", "dense"],
            reason="synthesis or comparison terms detected",
        )
    if re.search(r"\b[A-Z]{2,}[-_ ]?\d+\b", query) or re.search(r"\d", query):
        return QueryPlan(
            query_type="exact_lookup",
            routes=["bm25", "hybrid"],
            reason="identifier or numeric lookup detected",
        )
    return QueryPlan(
        query_type="semantic",
        routes=["hybrid"],
        reason="default semantic retrieval route",
    )
