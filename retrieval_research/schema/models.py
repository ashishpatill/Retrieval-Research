from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Block:
    id: str
    kind: str
    text: str
    page_number: int
    bbox: Optional[List[float]] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Page:
    id: str
    number: int
    text: str = ""
    image_path: Optional[str] = None
    blocks: List[Block] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    id: str
    source_path: str
    title: str
    created_at: str = field(default_factory=utc_now)
    pages: List[Page] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        pages = []
        for page_data in data.get("pages", []):
            blocks = [Block(**block) for block in page_data.get("blocks", [])]
            page = Page(
                id=page_data["id"],
                number=page_data["number"],
                text=page_data.get("text", ""),
                image_path=page_data.get("image_path"),
                blocks=blocks,
                metadata=page_data.get("metadata", {}),
            )
            pages.append(page)
        return cls(
            id=data["id"],
            source_path=data["source_path"],
            title=data["title"],
            created_at=data.get("created_at", utc_now()),
            pages=pages,
            metadata=data.get("metadata", {}),
        )


@dataclass
class DocumentProfile:
    document_id: str
    title: str
    source_type: str
    page_count: int
    text_page_count: int
    image_page_count: int
    total_words: int
    page_types: Dict[str, int]
    headings: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    extraction_confidence: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentProfile":
        return cls(**data)


@dataclass
class Chunk:
    id: str
    document_id: str
    page_numbers: List[int]
    text: str
    chunk_index: int
    parent_section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(**data)


@dataclass
class Evidence:
    chunk_id: str
    document_id: str
    page_numbers: List[int]
    text: str
    score: float
    retrieval_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Citation:
    id: str
    document_id: str
    chunk_id: str
    page_numbers: List[int]
    retrieval_path: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    text: str
    citation_ids: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeCard:
    query: str
    answer: str
    answerable: bool
    citations: List[Citation]
    claims: List[Claim]
    confidence: float = 0.0
    answerability_reason: str = ""
    unresolved_ambiguity: List[str] = field(default_factory=list)
    follow_up_retrieval_suggestions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResult:
    query: str
    evidence: List[Evidence]
    answer: str = ""
    knowledge_card: Optional[KnowledgeCard] = None
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalTrace:
    query: str
    mode: str
    document_ids: List[str]
    steps: List[Dict[str, Any]]
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
