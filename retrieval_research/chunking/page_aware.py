from __future__ import annotations

import re
from typing import List, Optional, Tuple

from retrieval_research.schema import Chunk, Document


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _words(text: str) -> List[str]:
    return re.findall(r"\S+", text)


def _page_segments(text: str) -> List[Tuple[Optional[str], List[str]]]:
    segments: List[Tuple[Optional[str], List[str]]] = []
    current_section: Optional[str] = None
    current_words: List[str] = []

    def flush() -> None:
        nonlocal current_words
        if current_words:
            segments.append((current_section, current_words))
            current_words = []

    for line in text.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            flush()
            current_section = match.group(2).strip()
        current_words.extend(_words(line))

    flush()
    return segments


def chunk_document(document: Document, max_words: int = 220, overlap_words: int = 40) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_index = 0

    for page in document.pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        for current_section, words in _page_segments(page_text):
            start = 0
            while start < len(words):
                end = min(start + max_words, len(words))
                text = " ".join(words[start:end]).strip()
                if text:
                    chunks.append(
                        Chunk(
                            id=f"{document.id}:chunk:{chunk_index}",
                            document_id=document.id,
                            page_numbers=[page.number],
                            text=text,
                            chunk_index=chunk_index,
                            parent_section=current_section,
                            metadata={
                                "strategy": "page_aware_words",
                                "word_start": start,
                                "word_end": end,
                                "source_page_id": page.id,
                            },
                        )
                    )
                    chunk_index += 1
                if end >= len(words):
                    break
                start = max(end - overlap_words, start + 1)

    return chunks
