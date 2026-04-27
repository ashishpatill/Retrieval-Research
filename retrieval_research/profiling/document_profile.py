from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

from retrieval_research.schema import Document, DocumentProfile


HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3}\b")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
TABLE_MARKERS = ("|---", "\t", " table ", " row ", " column ")

STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "between",
    "document",
    "from",
    "into",
    "more",
    "retrieval",
    "that",
    "their",
    "there",
    "these",
    "this",
    "with",
    "would",
}


def _page_type(text: str, has_image: bool) -> str:
    normalized = f" {text.lower()} "
    if any(marker in normalized for marker in TABLE_MARKERS):
        return "table_or_form"
    if has_image and not text.strip():
        return "image_only"
    if has_image:
        return "image_with_text"
    return "text"


def _headings(lines: Iterable[str], limit: int = 20) -> List[str]:
    found = []
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            found.append(match.group(1).strip())
        if len(found) >= limit:
            break
    return found


def _entities(text: str, limit: int = 20) -> List[str]:
    candidates = []
    for match in ENTITY_RE.finditer(text):
        value = match.group(0).strip()
        if len(value) < 3 or value.lower() in STOPWORDS:
            continue
        candidates.append(value)
    counts = Counter(candidates)
    return [value for value, _count in counts.most_common(limit)]


def _topics(text: str, limit: int = 12) -> List[str]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    counts = Counter(word for word in words if len(word) > 4 and word not in STOPWORDS)
    return [word for word, _count in counts.most_common(limit)]


def build_document_profile(document: Document) -> DocumentProfile:
    page_types = Counter()
    text_pages = 0
    image_pages = 0
    total_words = 0
    text_parts = []
    all_lines = []
    confidence_values = []

    for page in document.pages:
        text = page.text or ""
        words = WORD_RE.findall(text)
        has_text = bool(words)
        has_image = bool(page.image_path)

        text_pages += int(has_text)
        image_pages += int(has_image)
        total_words += len(words)
        text_parts.append(text)
        all_lines.extend(text.splitlines())
        page_types[_page_type(text, has_image)] += 1

        for block in page.blocks:
            if block.confidence is not None:
                confidence_values.append(block.confidence)

    source_type = str(document.metadata.get("source_type", "unknown"))
    extraction_confidence = {
        "ocr_run": document.metadata.get("ocr_run", source_type not in {"text", "md", "markdown"}),
        "has_page_images": image_pages > 0,
        "average_block_confidence": (
            sum(confidence_values) / len(confidence_values) if confidence_values else None
        ),
        "empty_page_count": sum(1 for page in document.pages if not (page.text or "").strip()),
    }

    full_text = "\n".join(text_parts)
    return DocumentProfile(
        document_id=document.id,
        title=document.title,
        source_type=source_type,
        page_count=len(document.pages),
        text_page_count=text_pages,
        image_page_count=image_pages,
        total_words=total_words,
        page_types=dict(page_types),
        headings=_headings(all_lines),
        topics=_topics(full_text),
        entities=_entities(full_text),
        extraction_confidence=extraction_confidence,
    )
