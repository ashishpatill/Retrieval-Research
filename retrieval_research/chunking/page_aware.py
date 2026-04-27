from __future__ import annotations

import re
from typing import List, Optional

from retrieval_research.schema import Chunk, Document


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _words(text: str) -> List[str]:
    return re.findall(r"\S+", text)


def _section_for_line(line: str, current: Optional[str]) -> Optional[str]:
    match = HEADING_RE.match(line.strip())
    if match:
        return match.group(2).strip()
    return current


def chunk_document(document: Document, max_words: int = 220, overlap_words: int = 40) -> List[Chunk]:
    chunks: List[Chunk] = []
    current_section: Optional[str] = None
    chunk_index = 0

    for page in document.pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        for line in page_text.splitlines():
            current_section = _section_for_line(line, current_section)

        words = _words(page_text)
        if not words:
            continue

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
