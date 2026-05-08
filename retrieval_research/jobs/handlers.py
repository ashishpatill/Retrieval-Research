from __future__ import annotations

from typing import Any, Dict

from retrieval_research.chunking import chunk_document
from retrieval_research.config import get_settings
from retrieval_research.ingest import ingest_path
from retrieval_research.log import get_logger
from retrieval_research.retrieval import build_indexes
from retrieval_research.storage import ArtifactStore

from .models import Job, JobType

_logger = get_logger("jobs.handler")


def _store() -> ArtifactStore:
    return ArtifactStore()


def handle_job(job: Job) -> Dict[str, Any]:
    store = _store()
    if job.type == JobType.INGEST:
        path = job.params["path"]
        ocr = job.params.get("ocr", False)
        mode = job.params.get("mode", "")
        dpi = job.params.get("dpi", 0)
        doc = ingest_path(path, store=store, run_ocr=ocr, mode=mode, dpi=dpi)
        return {"document_id": doc.id, "page_count": len(doc.pages)}

    if job.type == JobType.CHUNK:
        doc = store.load_document(job.params["document_id"])
        s = get_settings()
        chunks = chunk_document(
            doc,
            max_words=job.params.get("max_words", s.default_chunk_max_words),
            overlap_words=job.params.get("overlap_words", s.default_chunk_overlap_words),
        )
        path = store.save_chunks(doc.id, chunks)
        return {"document_id": doc.id, "chunk_count": len(chunks), "path": str(path)}

    if job.type == JobType.INDEX:
        paths = build_indexes(
            store,
            job.params["document_id"],
            mode=job.params.get("mode", "all"),
            visual_backend=job.params.get("visual_backend", ""),
            colpali_model=job.params.get("colpali_model", ""),
            visual_compression=job.params.get("visual_compression", ""),
            device=job.params.get("device", ""),
        )
        return {"document_id": job.params["document_id"], "paths": paths}

    if job.type == JobType.PIPELINE:
        ingest_params = job.params.get("ingest", {})
        doc = ingest_path(
            ingest_params["path"],
            store=store,
            run_ocr=ingest_params.get("ocr", False),
            mode=ingest_params.get("mode", ""),
            dpi=ingest_params.get("dpi", 0),
        )
        doc_id = doc.id
        s = get_settings()
        chunks = chunk_document(
            doc,
            max_words=job.params.get("max_words", s.default_chunk_max_words),
            overlap_words=job.params.get("overlap_words", s.default_chunk_overlap_words),
        )
        store.save_chunks(doc_id, chunks)
        idx_params = job.params.get("index", {})
        paths = build_indexes(
            store,
            doc_id,
            mode=idx_params.get("mode", "all"),
            visual_backend=idx_params.get("visual_backend", ""),
            colpali_model=idx_params.get("colpali_model", ""),
            visual_compression=idx_params.get("visual_compression", ""),
            device=idx_params.get("device", ""),
        )
        return {
            "document_id": doc_id,
            "ingest": {"page_count": len(doc.pages)},
            "chunk": {"chunk_count": len(chunks)},
            "index": {"paths": paths},
        }

    raise ValueError(f"Unknown job type: {job.type}")
