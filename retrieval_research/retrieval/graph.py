from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List

from retrieval_research.schema import Chunk, Evidence


TOKEN_RE = re.compile(r"[a-z0-9_]+")
ENTITY_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9&.-]*|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z0-9&.-]*|[A-Z]{2,})){0,3}\b")
SECTION_REF_RE = re.compile(r"\b(?:section|chapter|appendix)\s+([A-Z0-9][A-Za-z0-9 ._-]{0,60})", re.IGNORECASE)
NUMBERED_REF_RE = re.compile(r"\b(figure|fig\.|table|page|eq\.|equation)\s*([A-Z]?\d+(?:\.\d+)*)", re.IGNORECASE)
CITATION_REF_RE = re.compile(r"\[(\d{1,3})\]")

ENTITY_STOPWORDS = {
    "A",
    "An",
    "And",
    "For",
    "In",
    "No",
    "The",
    "This",
    "To",
}


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def _entities(text: str) -> set[str]:
    entities = set()
    for match in ENTITY_RE.finditer(text):
        value = " ".join(match.group(0).split())
        if len(value) < 3 or value in ENTITY_STOPWORDS:
            continue
        entities.add(value)
        parts = value.split()
        for start in range(len(parts)):
            for end in range(start + 1, min(len(parts), start + 3) + 1):
                sub_value = " ".join(parts[start:end])
                if len(sub_value) >= 3 and sub_value not in ENTITY_STOPWORDS:
                    entities.add(sub_value)
    return entities


def _references(text: str) -> set[str]:
    refs = set()
    for kind, number in NUMBERED_REF_RE.findall(text):
        normalized_kind = "figure" if kind.lower() == "fig." else kind.lower()
        refs.add(f"{normalized_kind}:{number.lower()}")
    for value in CITATION_REF_RE.findall(text):
        refs.add(f"citation:{value}")
    for value in SECTION_REF_RE.findall(text):
        label = re.split(r"[,.;\n]", value.strip(), maxsplit=1)[0].strip()
        if label:
            refs.add(f"section:{label.lower()}")
    return refs


def _section_key(section: str | None) -> str | None:
    if not section:
        return None
    return re.sub(r"\s+", " ", section.strip()).lower()


def _add_edge(edges: dict[str, list[dict]], source: str, target: str, relation: str, weight: float, **metadata: object) -> None:
    if source == target:
        return
    edge = {"target": target, "relation": relation, "weight": weight, **metadata}
    if edge not in edges[source]:
        edges[source].append(edge)


class GraphIndex:
    def __init__(self, chunks: List[Chunk], edges: Dict[str, List[dict]] | None = None):
        self.chunks = chunks
        self.by_id = {chunk.id: chunk for chunk in chunks}
        self.edges = edges or self._build_edges(chunks)
        self.stats = self._build_stats()
        self.knowledge_graph = self._build_knowledge_graph()
        self.last_diagnostics: dict = {}

    @staticmethod
    def _build_edges(chunks: List[Chunk]) -> Dict[str, List[dict]]:
        edges: dict[str, list[dict]] = defaultdict(list)
        by_page: dict[int, list[Chunk]] = defaultdict(list)
        by_section: dict[str, list[Chunk]] = defaultdict(list)
        by_entity: dict[str, list[Chunk]] = defaultdict(list)
        reference_sources: dict[str, list[Chunk]] = defaultdict(list)
        reference_targets: dict[str, list[Chunk]] = defaultdict(list)

        for chunk in chunks:
            for page in chunk.page_numbers:
                by_page[page].append(chunk)
                reference_targets[f"page:{page}"].append(chunk)
            section = _section_key(chunk.parent_section)
            if section:
                by_section[section].append(chunk)
                reference_targets[f"section:{section}"].append(chunk)
            for entity in _entities(chunk.text):
                by_entity[entity].append(chunk)
            for ref in _references(chunk.text):
                reference_sources[ref].append(chunk)
            for kind, number in NUMBERED_REF_RE.findall(chunk.text):
                normalized_kind = "figure" if kind.lower() == "fig." else kind.lower()
                if normalized_kind in {"figure", "table", "equation"}:
                    reference_targets[f"{normalized_kind}:{number.lower()}"].append(chunk)

        ordered = sorted(chunks, key=lambda chunk: chunk.chunk_index)
        for left, right in zip(ordered, ordered[1:]):
            _add_edge(edges, left.id, right.id, "next_chunk", 0.4)
            _add_edge(edges, right.id, left.id, "previous_chunk", 0.4)

        for page, page_chunks in by_page.items():
            ids = [chunk.id for chunk in page_chunks]
            for chunk_id in ids:
                for other_id in ids:
                    _add_edge(edges, chunk_id, other_id, "same_page", 0.3, page=page)

        for section, section_chunks in by_section.items():
            ids = [chunk.id for chunk in section_chunks]
            for chunk_id in ids:
                for other_id in ids:
                    _add_edge(edges, chunk_id, other_id, "same_section", 0.55, section=section)

        for entity, entity_chunks in by_entity.items():
            ids = [chunk.id for chunk in entity_chunks]
            if len(ids) < 2:
                continue
            for chunk_id in ids:
                for other_id in ids:
                    _add_edge(edges, chunk_id, other_id, "same_entity", 0.65, entity=entity)

        for ref, source_chunks in reference_sources.items():
            targets = reference_targets.get(ref, [])
            if not targets:
                continue
            for source in source_chunks:
                for target in targets:
                    _add_edge(edges, source.id, target.id, "reference", 0.75, reference=ref)
                    _add_edge(edges, target.id, source.id, "referenced_by", 0.35, reference=ref)

        return dict(edges)

    def _build_stats(self) -> dict:
        relation_counts = Counter(
            edge.get("relation", "linked")
            for edge_list in self.edges.values()
            for edge in edge_list
        )
        return {
            "node_count": len(self.chunks),
            "edge_count": sum(relation_counts.values()),
            "relation_counts": dict(sorted(relation_counts.items())),
        }

    def _build_knowledge_graph(self) -> dict:
        sections: dict[str, dict] = {}
        entities: dict[str, dict] = {}
        references: dict[str, dict] = {}

        for chunk in self.chunks:
            section = _section_key(chunk.parent_section)
            if section:
                sections.setdefault(
                    section,
                    {"name": chunk.parent_section, "chunk_ids": [], "document_ids": set(), "pages": set()},
                )
                sections[section]["chunk_ids"].append(chunk.id)
                sections[section]["document_ids"].add(chunk.document_id)
                sections[section]["pages"].update(chunk.page_numbers)

            for entity in _entities(chunk.text):
                entities.setdefault(entity, {"name": entity, "chunk_ids": [], "document_ids": set(), "pages": set()})
                entities[entity]["chunk_ids"].append(chunk.id)
                entities[entity]["document_ids"].add(chunk.document_id)
                entities[entity]["pages"].update(chunk.page_numbers)

            for ref in _references(chunk.text):
                references.setdefault(
                    ref,
                    {"reference": ref, "source_chunk_ids": [], "target_chunk_ids": [], "document_ids": set()},
                )
                references[ref]["source_chunk_ids"].append(chunk.id)
                references[ref]["document_ids"].add(chunk.document_id)

        for source_id, edge_list in self.edges.items():
            for edge in edge_list:
                ref = edge.get("reference")
                if not ref:
                    continue
                references.setdefault(
                    str(ref),
                    {"reference": str(ref), "source_chunk_ids": [], "target_chunk_ids": [], "document_ids": set()},
                )
                if source_id not in references[str(ref)]["source_chunk_ids"]:
                    references[str(ref)]["source_chunk_ids"].append(source_id)
                target = edge.get("target")
                if target and target not in references[str(ref)]["target_chunk_ids"]:
                    references[str(ref)]["target_chunk_ids"].append(target)
                source_chunk = self.by_id.get(source_id)
                target_chunk = self.by_id.get(str(target)) if target else None
                if source_chunk:
                    references[str(ref)]["document_ids"].add(source_chunk.document_id)
                if target_chunk:
                    references[str(ref)]["document_ids"].add(target_chunk.document_id)

        def _json_ready(items: dict[str, dict], page_key: str | None = "pages") -> list[dict]:
            ready = []
            for value in items.values():
                item = dict(value)
                item["chunk_ids"] = sorted(set(item.get("chunk_ids", [])))
                item["document_ids"] = sorted(item.get("document_ids", set()))
                if page_key and page_key in item:
                    item[page_key] = sorted(item[page_key])
                ready.append(item)
            return sorted(ready, key=lambda item: item.get("name") or item.get("reference", ""))

        reference_items = []
        for value in references.values():
            item = dict(value)
            item["source_chunk_ids"] = sorted(set(item.get("source_chunk_ids", [])))
            item["target_chunk_ids"] = sorted(set(item.get("target_chunk_ids", [])))
            item["document_ids"] = sorted(item.get("document_ids", set()))
            reference_items.append(item)

        return {
            "type": "knowledge_graph",
            "stats": {
                **self.stats,
                "section_count": len(sections),
                "entity_count": len(entities),
                "reference_count": len(references),
            },
            "sections": _json_ready(sections),
            "entities": _json_ready(entities),
            "references": sorted(reference_items, key=lambda item: item["reference"]),
        }

    def to_dict(self) -> dict:
        return {
            "type": "graph",
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "edges": self.edges,
            "stats": self.stats,
            "knowledge_graph": self.knowledge_graph,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GraphIndex":
        return cls(
            [Chunk.from_dict(item) for item in payload.get("chunks", [])],
            edges=payload.get("edges", {}),
        )

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        query_entities = _entities(query)
        query_refs = _references(query)

        seeds = []
        for chunk in self.chunks:
            chunk_tokens = _tokens(chunk.text)
            overlap = len(query_tokens & chunk_tokens)
            entity_overlap = len(query_entities & _entities(chunk.text))
            ref_overlap = len(query_refs & _references(chunk.text))
            score = (overlap / max(len(query_tokens), 1)) + (entity_overlap * 0.3) + (ref_overlap * 0.4)
            if score:
                seeds.append((chunk, score))

        seeds.sort(key=lambda item: item[1], reverse=True)
        scores: dict[str, float] = {}
        paths: dict[str, list[str]] = {}
        relation_counts: Counter[str] = Counter()
        expanded_from: dict[str, list[str]] = defaultdict(list)

        for chunk, score in seeds[: max(top_k, 8)]:
            scores[chunk.id] = max(scores.get(chunk.id, 0.0), score)
            paths.setdefault(chunk.id, []).append("seed")
            for edge in self.edges.get(chunk.id, []):
                target_id = edge["target"]
                propagated = score * float(edge.get("weight", 0.25))
                if propagated > scores.get(target_id, 0.0):
                    scores[target_id] = propagated
                paths.setdefault(target_id, []).append(edge.get("relation", "linked"))
                relation_counts[edge.get("relation", "linked")] += 1
                expanded_from[target_id].append(chunk.id)

        ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        self.last_diagnostics = {
            **self.stats,
            "seed_count": len(seeds),
            "expanded_count": max(0, len(scores) - min(len(seeds), len(scores))),
            "query_entities": sorted(query_entities),
            "query_references": sorted(query_refs),
            "expanded_relation_counts": dict(sorted(relation_counts.items())),
        }
        evidence = []
        for chunk_id in ranked_ids:
            chunk = self.by_id.get(chunk_id)
            if not chunk:
                continue
            evidence.append(
                Evidence(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    page_numbers=chunk.page_numbers,
                    text=chunk.text,
                    score=scores[chunk_id],
                    retrieval_path="graph",
                    metadata={
                        **chunk.metadata,
                        "graph_relations": sorted(set(paths.get(chunk_id, []))),
                        "graph_expanded_from": sorted(set(expanded_from.get(chunk_id, []))),
                    },
                )
            )
        return evidence
