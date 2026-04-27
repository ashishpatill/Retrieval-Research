from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import List, Optional

from PIL import Image

from retrieval_research.profiling import build_document_profile
from retrieval_research.schema import Document, Page
from retrieval_research.storage import ArtifactStore


DEFAULT_SYSTEM = "You are an expert document parser. Extract content accurately and preserve structure."
DEFAULT_QUERY = "Extract all text, tables as Markdown, formulas as LaTeX. Return clean structured output."


def stable_document_id(path: Path, content: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(str(path).encode("utf-8"))
    digest.update(content[:1024 * 1024])
    return digest.hexdigest()[:16]


def _document_from_text(path: Path, text: str, document_id: str) -> Document:
    return Document(
        id=document_id,
        source_path=str(path),
        title=path.stem,
        pages=[Page(id=f"{document_id}:page:1", number=1, text=text)],
        metadata={"source_type": path.suffix.lower().lstrip(".") or "text"},
    )


def _document_from_history(path: Path, document_id: str) -> Document:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages: List[Page] = []
    page_idx = 1
    for file_data in payload.get("results", []):
        for page in file_data.get("pages", []):
            pages.append(
                Page(
                    id=f"{document_id}:page:{page_idx}",
                    number=page_idx,
                    text=page.get("final") or page.get("glm") or "",
                    metadata={
                        "source_filename": file_data.get("filename"),
                        "source_page": page.get("page"),
                        "glm_text": page.get("glm", ""),
                    },
                )
            )
            page_idx += 1
    return Document(
        id=document_id,
        source_path=str(path),
        title=path.stem,
        pages=pages,
        metadata={"source_type": "history_json", "original_timestamp": payload.get("timestamp")},
    )


def _save_image_page(store: ArtifactStore, document_id: str, image: Image.Image, page_number: int) -> str:
    page_path = store.page_dir(document_id) / f"page_{page_number:04d}.png"
    image.save(page_path, format="PNG")
    return str(page_path)


def _ocr_image(image: Image.Image, mode: str, system_prompt: str, user_query: str) -> str:
    from core_processor import process_page

    _glm, final = process_page(image, mode, system_prompt, user_query)
    return final


def _document_from_image(
    path: Path,
    content: bytes,
    document_id: str,
    store: ArtifactStore,
    run_ocr: bool,
    mode: str,
    system_prompt: str,
    user_query: str,
) -> Document:
    image = Image.open(io.BytesIO(content)).convert("RGB")
    image_path = _save_image_page(store, document_id, image, 1)
    text = _ocr_image(image, mode, system_prompt, user_query) if run_ocr else ""
    return Document(
        id=document_id,
        source_path=str(path),
        title=path.stem,
        pages=[Page(id=f"{document_id}:page:1", number=1, text=text, image_path=image_path)],
        metadata={"source_type": "image", "ocr_run": run_ocr},
    )


def _document_from_pdf(
    path: Path,
    content: bytes,
    document_id: str,
    store: ArtifactStore,
    run_ocr: bool,
    mode: str,
    system_prompt: str,
    user_query: str,
    dpi: int,
) -> Document:
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(content, dpi=dpi)
    pages = []
    for idx, image in enumerate(images, 1):
        image = image.convert("RGB")
        image_path = _save_image_page(store, document_id, image, idx)
        text = _ocr_image(image, mode, system_prompt, user_query) if run_ocr else ""
        pages.append(Page(id=f"{document_id}:page:{idx}", number=idx, text=text, image_path=image_path))
    return Document(
        id=document_id,
        source_path=str(path),
        title=path.stem,
        pages=pages,
        metadata={"source_type": "pdf", "ocr_run": run_ocr, "dpi": dpi},
    )


def ingest_path(
    path: str,
    store: Optional[ArtifactStore] = None,
    run_ocr: bool = False,
    mode: str = "Hybrid",
    system_prompt: str = DEFAULT_SYSTEM,
    user_query: str = DEFAULT_QUERY,
    dpi: int = 150,
) -> Document:
    store = store or ArtifactStore()
    source = Path(path)
    content = source.read_bytes()
    document_id = stable_document_id(source, content)
    store.copy_raw(source, document_id)

    suffix = source.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        document = _document_from_text(source, content.decode("utf-8", errors="replace"), document_id)
    elif suffix == ".json":
        document = _document_from_history(source, document_id)
    elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}:
        document = _document_from_image(source, content, document_id, store, run_ocr, mode, system_prompt, user_query)
    elif suffix == ".pdf":
        document = _document_from_pdf(source, content, document_id, store, run_ocr, mode, system_prompt, user_query, dpi)
    else:
        raise ValueError(f"Unsupported input type: {suffix or source.name}")

    store.save_document(document)
    store.save_document_profile(build_document_profile(document))
    return document
