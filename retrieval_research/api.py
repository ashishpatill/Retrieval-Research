from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from retrieval_research.chunking import chunk_document
from retrieval_research.evaluation.runner import report_to_markdown, run_eval
from retrieval_research.evidence import build_knowledge_card
from retrieval_research.ingest import ingest_path
from retrieval_research.config import get_settings
from retrieval_research.jobs import JobStore, JobType, JobStatus
from retrieval_research.retrieval import (
    DEFAULT_RERANK_OVERLAP_WEIGHT,
    DEFAULT_PLANNER_RERANK,
    DEFAULT_ROUTE_VOTE_BONUS,
    DEFAULT_COLPALI_MODEL,
    PLANNER_MERGE_STRATEGIES,
    RETRIEVAL_MODES,
    build_indexes,
    search_corpus,
)
from retrieval_research.schema import RetrievalResult, RetrievalTrace
from retrieval_research.storage import ArtifactStore


_settings = get_settings()


class ChunkRequest(BaseModel):
    max_words: int = Field(default=_settings.default_chunk_max_words, ge=20, le=2000)
    overlap_words: int = Field(default=_settings.default_chunk_overlap_words, ge=0, le=500)


class IndexRequest(BaseModel):
    mode: str = "all"
    visual_backend: str = ""
    visual_compression: str = ""
    colpali_model: str = ""
    device: str = ""


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: Optional[str] = None
    top_k: int = Field(default=_settings.default_top_k, ge=1, le=50)
    mode: str = ""
    planner_merge_strategy: str = ""
    planner_rerank: bool = DEFAULT_PLANNER_RERANK
    planner_route_vote_bonus: float = Field(default=DEFAULT_ROUTE_VOTE_BONUS, ge=0.0, le=1.0)
    planner_rerank_overlap_weight: float = Field(default=DEFAULT_RERANK_OVERLAP_WEIGHT, ge=0.0, le=1.0)


class EvalRequest(BaseModel):
    manifest: Dict[str, Any]
    top_k: int = Field(default=_settings.default_top_k, ge=1, le=50)
    modes: List[str] = Field(default_factory=lambda: list(RETRIEVAL_MODES))
    planner_merge_strategy: str = ""
    planner_rerank: bool = DEFAULT_PLANNER_RERANK
    planner_route_vote_bonus: float = Field(default=DEFAULT_ROUTE_VOTE_BONUS, ge=0.0, le=1.0)
    planner_rerank_overlap_weight: float = Field(default=DEFAULT_RERANK_OVERLAP_WEIGHT, ge=0.0, le=1.0)
    planner_sweep: bool = False


def create_app(store_root: str | None = None) -> FastAPI:
    resolved_root = store_root if store_root is not None else get_settings().data_root
    app = FastAPI(title="Retrieval Research API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _store() -> ArtifactStore:
        return ArtifactStore(resolved_root)

    def _job_store() -> JobStore:
        return JobStore()

    # ── Health ────────────────────────────────────────────────────────────

    try:
        from core_processor.mlx_backend import is_mlx_available as _is_mlx_available
    except Exception:
        _is_mlx_available = lambda: False  # type: ignore[assignment]

    @app.get("/api/health")
    def health() -> Dict[str, Any]:
        gemini_ok = bool(_settings.gemini_api_key)
        return {
            "status": "ok",
            "service": "retrieval-research-api",
            "version": "0.1.0",
            "mlx_available": _is_mlx_available(),
            "gemini_configured": gemini_ok,
        }

    # ── Documents ─────────────────────────────────────────────────────────

    @app.get("/api/documents")
    def list_documents() -> Dict[str, Any]:
        store = _store()
        items = []
        for document in sorted(store.list_documents(), key=lambda item: item.created_at, reverse=True):
            try:
                profile = store.load_document_profile(document.id).to_dict()
            except FileNotFoundError:
                profile = None
            items.append(
                {
                    "id": document.id,
                    "title": document.title,
                    "source_path": document.source_path,
                    "created_at": document.created_at,
                    "page_count": len(document.pages),
                    "source_type": document.metadata.get("source_type"),
                    "profile": profile,
                }
            )
        return {"documents": items}

    @app.get("/api/documents/{document_id}")
    def document_detail(document_id: str) -> Dict[str, Any]:
        store = _store()
        try:
            document = store.load_document(document_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}") from exc

        try:
            profile = store.load_document_profile(document_id).to_dict()
        except FileNotFoundError:
            profile = None
        try:
            chunks = store.load_chunks(document_id)
            chunk_count = len(chunks)
        except FileNotFoundError:
            chunk_count = 0
        try:
            knowledge_graph = store.load_knowledge_graph(document_id)
            graph_stats = knowledge_graph.get("stats", {})
        except FileNotFoundError:
            knowledge_graph = None
            graph_stats = None

        def _index_ready(name: str) -> bool:
            try:
                store.load_index(document_id, name)
                return True
            except FileNotFoundError:
                return False

        return {
            "document": document.to_dict(),
            "profile": profile,
            "stats": {
                "chunk_count": chunk_count,
                "indexes": {
                    "bm25": _index_ready("bm25"),
                    "dense": _index_ready("dense"),
                    "late": _index_ready("late"),
                    "visual": _index_ready("visual"),
                    "graph": _index_ready("graph"),
                },
                "knowledge_graph": graph_stats,
            },
            "knowledge_graph": knowledge_graph,
        }

    # ── Ingest (sync + async) ─────────────────────────────────────────────

    @app.post("/api/documents/ingest")
    async def ingest_document(
        file: UploadFile = File(...),
        ocr: bool = Form(False),
        mode: str = Form(""),
        dpi: int = Form(0),
        sync: bool = Query(False, description="Run synchronously and return the document directly"),
    ) -> Dict[str, Any]:
        settings = get_settings()
        mode = mode or settings.default_ocr_mode
        dpi = dpi or settings.default_dpi
        content = await file.read()
        suffix = Path(file.filename or "upload.bin").suffix

        if sync:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp.write(content)
                temp_path = temp.name
            try:
                document = ingest_path(temp_path, store=_store(), run_ocr=ocr, mode=mode, dpi=dpi)
            finally:
                Path(temp_path).unlink(missing_ok=True)
            return {"document_id": document.id, "document": document.to_dict()}

        store = _store()
        job_id = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        persistent_path = store.raw_dir / job_id / (file.filename or "upload.bin")
        persistent_path.parent.mkdir(parents=True, exist_ok=True)
        persistent_path.write_bytes(content)
        job = _job_store().submit(
            JobType.INGEST,
            {"path": str(persistent_path), "ocr": ocr, "mode": mode, "dpi": dpi},
        )
        return {"job_id": job.job_id, "status": job.status.value}

    # ── Chunk (sync + async) ──────────────────────────────────────────────

    def _chunk_sync(document_id: str, max_words: int, overlap_words: int) -> Dict[str, Any]:
        store = _store()
        try:
            document = store.load_document(document_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}") from exc
        chunks = chunk_document(document, max_words=max_words, overlap_words=overlap_words)
        path = store.save_chunks(document_id, chunks)
        return {"document_id": document_id, "chunk_count": len(chunks), "saved_path": str(path)}

    @app.post("/api/documents/{document_id}/chunk")
    def chunk_endpoint(
        document_id: str,
        payload: ChunkRequest,
        sync: bool = Query(False, description="Run synchronously and return results directly"),
    ) -> Dict[str, Any]:
        if sync:
            return _chunk_sync(document_id, payload.max_words, payload.overlap_words)
        job = _job_store().submit(
            JobType.CHUNK,
            {
                "document_id": document_id,
                "max_words": payload.max_words,
                "overlap_words": payload.overlap_words,
            },
        )
        return {"job_id": job.job_id, "status": job.status.value}

    # ── Index (sync + async) ──────────────────────────────────────────────

    def _index_sync(document_id: str, payload: IndexRequest) -> Dict[str, Any]:
        store = _store()
        supported_index_modes = {"all", *RETRIEVAL_MODES}
        if payload.mode not in supported_index_modes:
            raise HTTPException(status_code=400, detail=f"Unsupported index mode: {payload.mode}")
        try:
            paths = build_indexes(
                store,
                document_id,
                mode=payload.mode,
                visual_backend=payload.visual_backend,
                colpali_model=payload.colpali_model,
                visual_compression=payload.visual_compression,
                device=payload.device,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Missing chunks or document: {document_id}") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"document_id": document_id, "saved_paths": paths}

    @app.post("/api/documents/{document_id}/index")
    def index_endpoint(
        document_id: str,
        payload: IndexRequest,
        sync: bool = Query(False, description="Run synchronously and return results directly"),
    ) -> Dict[str, Any]:
        supported_index_modes = {"all", *RETRIEVAL_MODES}
        if payload.mode not in supported_index_modes:
            raise HTTPException(status_code=400, detail=f"Unsupported index mode: {payload.mode}")
        if sync:
            return _index_sync(document_id, payload)
        job = _job_store().submit(
            JobType.INDEX,
            {
                "document_id": document_id,
                "mode": payload.mode,
                "visual_backend": payload.visual_backend,
                "colpali_model": payload.colpali_model,
                "visual_compression": payload.visual_compression,
                "device": payload.device,
            },
        )
        return {"job_id": job.job_id, "status": job.status.value}

    # ── Pipeline (ingest + chunk + index) ─────────────────────────────────

    @app.post("/api/documents/pipeline")
    async def pipeline_document(
        file: UploadFile = File(...),
        ocr: bool = Form(False),
        mode: str = Form(""),
        dpi: int = Form(0),
        index_mode: str = Form("all"),
        visual_backend: str = Form(""),
        colpali_model: str = Form(""),
        visual_compression: str = Form(""),
        device: str = Form(""),
        sync: bool = Query(False, description="Run synchronously and return results directly"),
    ) -> Dict[str, Any]:
        settings = get_settings()
        mode = mode or settings.default_ocr_mode
        dpi = dpi or settings.default_dpi
        content = await file.read()
        suffix = Path(file.filename or "upload.bin").suffix

        if sync:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp.write(content)
                temp_path = temp.name
            try:
                doc = ingest_path(temp_path, store=_store(), run_ocr=ocr, mode=mode, dpi=dpi)
            finally:
                Path(temp_path).unlink(missing_ok=True)
            store = _store()
            chunks = chunk_document(doc)
            store.save_chunks(doc.id, chunks)
            paths = build_indexes(store, doc.id, mode=index_mode)
            return {
                "document_id": doc.id,
                "page_count": len(doc.pages),
                "chunk_count": len(chunks),
                "index_paths": paths,
            }

        store = _store()
        job_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        persistent_path = store.raw_dir / job_id / (file.filename or "upload.bin")
        persistent_path.parent.mkdir(parents=True, exist_ok=True)
        persistent_path.write_bytes(content)
        job = _job_store().submit(
            JobType.PIPELINE,
            {
                "ingest": {"path": str(persistent_path), "ocr": ocr, "mode": mode, "dpi": dpi},
                "index": {
                    "mode": index_mode,
                    "visual_backend": visual_backend,
                    "colpali_model": colpali_model or DEFAULT_COLPALI_MODEL,
                    "visual_compression": visual_compression,
                    "device": device,
                },
            },
        )
        return {"job_id": job.job_id, "status": job.status.value}

    # ── Query ─────────────────────────────────────────────────────────────

    @app.post("/api/query")
    def query_endpoint(payload: QueryRequest) -> Dict[str, Any]:
        if payload.mode and payload.mode not in RETRIEVAL_MODES:
            raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode: {payload.mode}")
        if payload.planner_merge_strategy and payload.planner_merge_strategy not in PLANNER_MERGE_STRATEGIES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported planner merge strategy: {payload.planner_merge_strategy}",
            )

        store = _store()
        if payload.document_id:
            try:
                store.load_document(payload.document_id)
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=f"Document not found: {payload.document_id}") from exc
        document_ids = (
            [payload.document_id]
            if payload.document_id
            else [document.id for document in store.list_documents()]
        )
        if not document_ids:
            raise HTTPException(status_code=400, detail="No documents available; ingest a document first.")
        evidence, steps = search_corpus(
            store,
            document_ids,
            payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
            planner_merge_strategy=payload.planner_merge_strategy,
            planner_rerank=payload.planner_rerank,
            planner_route_vote_bonus=payload.planner_route_vote_bonus,
            planner_rerank_overlap_weight=payload.planner_rerank_overlap_weight,
        )
        knowledge_card = build_knowledge_card(payload.question, evidence)
        result = RetrievalResult(
            query=payload.question,
            evidence=evidence,
            answer=knowledge_card.answer,
            knowledge_card=knowledge_card,
        )
        trace = RetrievalTrace(
            query=payload.question,
            mode=payload.mode or get_settings().default_retrieval_mode,
            document_ids=document_ids,
            steps=steps,
        )
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        store.save_run(run_id, "evidence_bundle.json", result.to_dict())
        store.save_run(run_id, "knowledge_card.json", knowledge_card.to_dict())
        store.save_run(run_id, "retrieval_trace.json", trace.to_dict())
        return {"run_id": run_id, "result": result.to_dict(), "trace": trace.to_dict()}

    # ── Runs ──────────────────────────────────────────────────────────────

    @app.get("/api/runs")
    def list_runs() -> Dict[str, Any]:
        return {"runs": _store().list_runs()}

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str) -> Dict[str, Any]:
        store = _store()
        run_dir = store.runs_dir / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        payload = {"id": run_id, "files": {}}
        for file_path in sorted(run_dir.glob("*.json")):
            payload["files"][file_path.name] = store.load_json(file_path)
        return payload

    # ── Eval ──────────────────────────────────────────────────────────────

    @app.post("/api/eval")
    def eval_endpoint(payload: EvalRequest) -> Dict[str, Any]:
        for mode in payload.modes:
            if mode not in RETRIEVAL_MODES:
                raise HTTPException(status_code=400, detail=f"Unsupported eval mode: {mode}")
        if payload.planner_merge_strategy and payload.planner_merge_strategy not in PLANNER_MERGE_STRATEGIES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported planner merge strategy: {payload.planner_merge_strategy}",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp:
            temp.write(json.dumps(payload.manifest).encode("utf-8"))
            temp_path = temp.name

        store = _store()
        try:
            report = run_eval(
                temp_path,
                store=store,
                top_k=payload.top_k,
                modes=payload.modes,
                planner_merge_strategy=payload.planner_merge_strategy,
                planner_rerank=payload.planner_rerank,
                planner_route_vote_bonus=payload.planner_route_vote_bonus,
                planner_rerank_overlap_weight=payload.planner_rerank_overlap_weight,
                planner_sweep=payload.planner_sweep,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        json_path = store.save_run(run_id, "eval_report.json", report)
        markdown = report_to_markdown(report)
        md_path = store.runs_dir / run_id / "eval_report.md"
        md_path.write_text(markdown, encoding="utf-8")
        return {"run_id": run_id, "eval_report_path": str(json_path), "eval_markdown_path": str(md_path), "report": report}

    # ── Jobs ──────────────────────────────────────────────────────────────

    @app.get("/api/jobs")
    def list_jobs(status: Optional[str] = Query(None, description="Filter by job status")) -> Dict[str, Any]:
        js = _job_store()
        if status:
            try:
                filter_status = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid job status: {status}")
            jobs = js.list_jobs(status=filter_status)
        else:
            jobs = js.list_jobs()
        return {
            "jobs": [
                {"job_id": j.job_id, "type": j.type.value, "status": j.status.value, "created_at": j.created_at, "error": j.error}
                for j in jobs
            ]
        }

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str) -> Dict[str, Any]:
        js = _job_store()
        job = js.load(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return job.to_dict()

    return app


app = create_app()
