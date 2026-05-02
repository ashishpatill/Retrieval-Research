from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageFilter, ImageStat

from retrieval_research.retrieval.dense import cosine, hashed_embedding
from retrieval_research.schema import Document, Evidence, Page


class VisualPageIndex:
    def __init__(self, document: Document, dimensions: int = 384):
        self.document_id = document.id
        self.title = document.title
        self.pages = list(document.pages)
        self.dimensions = dimensions
        self.vectors = [hashed_embedding(self._page_text(page), dimensions=dimensions) for page in self.pages]

    def _profile_tokens(self, page: Page) -> list[str]:
        tokens = ["layout_unknown"]
        image_path = page.image_path
        if not image_path or not Path(image_path).exists():
            return tokens
        try:
            with Image.open(image_path).convert("L") as raw:
                width, height = raw.size
                stat = ImageStat.Stat(raw)
                mean = float(stat.mean[0])
                stddev = float(stat.stddev[0])
                entropy = float(raw.entropy())
                edge = raw.filter(ImageFilter.FIND_EDGES)
                edge_mean = float(ImageStat.Stat(edge).mean[0])
        except Exception:
            return tokens

        tokens = ["layout_visual"]
        if width and height:
            ratio = width / max(1, height)
            if ratio > 1.35:
                tokens.append("orientation_landscape")
            elif ratio < 0.8:
                tokens.append("orientation_portrait")
            else:
                tokens.append("orientation_square")

        if entropy > 5.4:
            tokens.append("texture_high")
        elif entropy < 4.0:
            tokens.append("texture_low")
        if stddev > 62:
            tokens.append("contrast_high")
        elif stddev < 36:
            tokens.append("contrast_low")
        if edge_mean > 28:
            tokens.append("line_density_high")
        elif edge_mean < 15:
            tokens.append("line_density_low")
        if mean < 95:
            tokens.append("brightness_low")
        elif mean > 180:
            tokens.append("brightness_high")
        return tokens

    def _page_text(self, page: Page) -> str:
        visual_tags = ["page document"]
        if page.image_path:
            visual_tags.extend(["page image visual layout scan figure diagram"])
        source_type = page.metadata.get("source_type") or ""
        if source_type:
            visual_tags.append(str(source_type))
        profile_tokens = self._profile_tokens(page)
        return " ".join([self.title, page.text, " ".join(visual_tags), " ".join(profile_tokens)]).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "visual_page_baseline",
            "document_id": self.document_id,
            "title": self.title,
            "dimensions": self.dimensions,
            "pages": [
                {
                    "id": page.id,
                    "number": page.number,
                    "text": page.text,
                    "image_path": page.image_path,
                    "metadata": page.metadata,
                }
                for page in self.pages
            ],
            "vectors": self.vectors,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "VisualPageIndex":
        pages = [
            Page(
                id=item["id"],
                number=item["number"],
                text=item.get("text", ""),
                image_path=item.get("image_path"),
                metadata=item.get("metadata", {}),
            )
            for item in payload.get("pages", [])
        ]
        document = Document(
            id=payload["document_id"],
            source_path="",
            title=payload.get("title", ""),
            pages=pages,
            metadata={"source": "visual_page_index"},
        )
        index = cls(document, dimensions=payload.get("dimensions", 384))
        if "vectors" in payload:
            index.vectors = payload["vectors"]
        return index

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        query_vector = hashed_embedding(query, dimensions=self.dimensions)
        scores: List[Tuple[int, float]] = []
        for idx, vector in enumerate(self.vectors):
            score = cosine(query_vector, vector)
            page = self.pages[idx]
            if page.image_path and any(term in query.lower() for term in ["page", "image", "figure", "diagram", "visual"]):
                score += 0.05
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        evidence = []
        for idx, score in scores[:top_k]:
            page = self.pages[idx]
            text = page.text.strip() or f"Visual page evidence for page {page.number}."
            evidence.append(
                Evidence(
                    chunk_id=page.id,
                    document_id=self.document_id,
                    page_numbers=[page.number],
                    text=text,
                    score=score,
                    retrieval_path="visual",
                    metadata={
                        "image_path": page.image_path,
                        "page_id": page.id,
                        "visual_profile": self._profile_tokens(page),
                    },
                )
            )
        return evidence


def load_visual_index(payload: Dict[str, Any]):
    if payload.get("kind") == "colpali_engine":
        from retrieval_research.retrieval.colpali import ColPaliPageIndex

        return ColPaliPageIndex.from_dict(payload)
    return VisualPageIndex.from_dict(payload)
