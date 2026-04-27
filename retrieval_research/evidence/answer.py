from __future__ import annotations

from typing import Iterable

from retrieval_research.schema import Evidence


def build_extractive_answer(query: str, evidence: Iterable[Evidence]) -> str:
    items = list(evidence)
    if not items:
        return "No evidence found for this query."

    lines = [f"Query: {query}", "", "Top evidence:"]
    for idx, item in enumerate(items, 1):
        citation = f"{item.document_id}, page(s) {', '.join(str(p) for p in item.page_numbers)}"
        snippet = item.text.strip().replace("\n", " ")
        if len(snippet) > 500:
            snippet = snippet[:497].rstrip() + "..."
        lines.append(f"{idx}. {snippet} [{citation}]")
    return "\n".join(lines)
