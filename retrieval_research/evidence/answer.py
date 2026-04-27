from __future__ import annotations

from typing import Iterable

from retrieval_research.schema import Citation, Claim, Evidence, KnowledgeCard


def _snippet(text: str, max_chars: int = 500) -> str:
    snippet = text.strip().replace("\n", " ")
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 3].rstrip() + "..."
    return snippet


def _confidence_from_evidence(items: list[Evidence]) -> float:
    if not items:
        return 0.0
    top_scores = [max(0.0, min(1.0, item.score)) for item in items[:3]]
    return sum(top_scores) / len(top_scores)


def build_knowledge_card(query: str, evidence: Iterable[Evidence]) -> KnowledgeCard:
    items = list(evidence)
    if not items:
        return KnowledgeCard(
            query=query,
            answer="No evidence found for this query.",
            answerable=False,
            confidence=0.0,
            answerability_reason="No retrieval hits were returned.",
            citations=[],
            claims=[],
            unresolved_ambiguity=["No retrieved evidence was available to support an answer."],
        )

    citations = [
        Citation(
            id=f"C{idx}",
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            page_numbers=item.page_numbers,
            retrieval_path=item.retrieval_path,
            score=item.score,
        )
        for idx, item in enumerate(items, 1)
    ]
    claims = [
        Claim(
            text=_snippet(item.text),
            citation_ids=[citations[idx - 1].id],
            confidence=max(0.0, min(1.0, item.score)),
        )
        for idx, item in enumerate(items, 1)
    ]

    lines = [f"Query: {query}", "", "Grounded answer:"]
    for claim in claims:
        citation = citations[int(claim.citation_ids[0][1:]) - 1]
        pages = ", ".join(str(page) for page in citation.page_numbers)
        lines.append(f"- {claim.text} [{citation.id}: {citation.document_id}/{citation.chunk_id}, page(s) {pages}]")

    confidence = _confidence_from_evidence(items)
    answerable = len(citations) > 0
    reason = (
        f"Evidence confidence is {confidence:.2f} across top retrieval hits."
        if answerable
        else f"Evidence confidence is too low ({confidence:.2f}) for a reliable grounded answer."
    )

    return KnowledgeCard(
        query=query,
        answer="\n".join(lines),
        answerable=answerable,
        citations=citations,
        claims=claims,
        confidence=confidence,
        answerability_reason=reason,
    )


def build_extractive_answer(query: str, evidence: Iterable[Evidence]) -> str:
    return build_knowledge_card(query, evidence).answer
