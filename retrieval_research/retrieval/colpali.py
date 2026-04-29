from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from retrieval_research.retrieval.compression import maybe_compress_embeddings, maybe_decompress_embedding
from retrieval_research.schema import Document, Evidence, Page


DEFAULT_COLPALI_MODEL = "vidore/colpali-v1.2"


class ColPaliUnavailableError(RuntimeError):
    pass


def _load_runtime():
    try:
        import torch
        from PIL import Image
        from colpali_engine.models import ColPali, ColPaliProcessor
    except ImportError as exc:
        raise ColPaliUnavailableError(
            "ColPali backend requires optional dependencies. Install with "
            "`pip install colpali-engine torch`, then rebuild the visual index "
            "with `--visual-backend colpali`."
        ) from exc
    return torch, Image, ColPali, ColPaliProcessor


def _default_device(torch_module) -> str:
    if torch_module.cuda.is_available():
        return "cuda:0"
    if getattr(torch_module.backends, "mps", None) and torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


def _page_payload(page: Page) -> Dict[str, Any]:
    return {
        "id": page.id,
        "number": page.number,
        "text": page.text,
        "image_path": page.image_path,
        "metadata": page.metadata,
    }


def _page_from_payload(payload: Dict[str, Any]) -> Page:
    return Page(
        id=payload["id"],
        number=payload["number"],
        text=payload.get("text", ""),
        image_path=payload.get("image_path"),
        metadata=payload.get("metadata", {}),
    )


class ColPaliPageIndex:
    def __init__(
        self,
        document_id: str,
        title: str,
        pages: List[Page],
        embeddings: List[Any],
        model_name: str = DEFAULT_COLPALI_MODEL,
        device: str = "auto",
        compression: str = "none",
    ):
        self.document_id = document_id
        self.title = title
        self.pages = pages
        self.embeddings = embeddings
        self.model_name = model_name
        self.device = device
        self.compression = compression

    @classmethod
    def build(
        cls,
        document: Document,
        model_name: str = DEFAULT_COLPALI_MODEL,
        device: str = "auto",
        compression: str = "none",
    ) -> "ColPaliPageIndex":
        torch, Image, ColPali, ColPaliProcessor = _load_runtime()
        resolved_device = _default_device(torch) if device == "auto" else device
        dtype = torch.bfloat16 if resolved_device != "cpu" else torch.float32

        pages = [page for page in document.pages if page.image_path and Path(page.image_path).exists()]
        if not pages:
            raise ValueError("ColPali visual indexing requires persisted page images.")

        model = ColPali.from_pretrained(
            model_name,
            torch_dtype=dtype,
            device_map=resolved_device,
        ).eval()
        processor = ColPaliProcessor.from_pretrained(model_name)
        images = [Image.open(page.image_path).convert("RGB") for page in pages]
        batch_images = processor.process_images(images).to(model.device)
        with torch.no_grad():
            image_embeddings = model(**batch_images)
        embeddings = [embedding.detach().cpu().float().tolist() for embedding in image_embeddings]
        stored_embeddings = maybe_compress_embeddings(embeddings, compression=compression)
        return cls(
            document_id=document.id,
            title=document.title,
            pages=pages,
            embeddings=stored_embeddings,
            model_name=model_name,
            device=resolved_device,
            compression=compression,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "colpali_engine",
            "document_id": self.document_id,
            "title": self.title,
            "model_name": self.model_name,
            "device": self.device,
            "embedding_compression": self.compression,
            "pages": [_page_payload(page) for page in self.pages],
            "embeddings": self.embeddings,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ColPaliPageIndex":
        return cls(
            document_id=payload["document_id"],
            title=payload.get("title", ""),
            pages=[_page_from_payload(item) for item in payload.get("pages", [])],
            embeddings=payload.get("embeddings", []),
            model_name=payload.get("model_name", DEFAULT_COLPALI_MODEL),
            device=payload.get("device", "auto"),
            compression=payload.get("embedding_compression", "none"),
        )

    def search(self, query: str, top_k: int = 5) -> List[Evidence]:
        torch, _Image, ColPali, ColPaliProcessor = _load_runtime()
        resolved_device = _default_device(torch) if self.device == "auto" else self.device
        dtype = torch.bfloat16 if resolved_device != "cpu" else torch.float32
        model = ColPali.from_pretrained(
            self.model_name,
            torch_dtype=dtype,
            device_map=resolved_device,
        ).eval()
        processor = ColPaliProcessor.from_pretrained(self.model_name)
        batch_query = processor.process_queries([query]).to(model.device)
        with torch.no_grad():
            query_embedding = model(**batch_query)

        page_embeddings = [
            torch.tensor(maybe_decompress_embedding(item), dtype=torch.float32, device=model.device)
            for item in self.embeddings
        ]
        scores_tensor = processor.score_multi_vector(query_embedding, page_embeddings)[0]
        scores: List[Tuple[int, float]] = [
            (idx, float(score)) for idx, score in enumerate(scores_tensor.detach().cpu().tolist())
        ]
        scores.sort(key=lambda item: item[1], reverse=True)

        evidence = []
        for idx, score in scores[:top_k]:
            page = self.pages[idx]
            text = page.text.strip() or f"ColPali visual page evidence for page {page.number}."
            evidence.append(
                Evidence(
                    chunk_id=page.id,
                    document_id=self.document_id,
                    page_numbers=[page.number],
                    text=text,
                    score=score,
                    retrieval_path="visual:colpali",
                    metadata={
                        "image_path": page.image_path,
                        "page_id": page.id,
                        "model_name": self.model_name,
                        "embedding_compression": self.compression,
                    },
                )
            )
        return evidence
