# 🧠 Retrieval-Research

Ideating, experimenting, optimising and testing Retrieval

**State-of-the-Art 2026 Document Parser** — GLM-OCR (local) + Gemini 3.1 Pro Preview (`gemini-3.1-pro-preview`)

Features:

- Batch processing (100+ pages)
- Streamlit + Gradio interfaces
- Pure Local / Pure Gemini / Hybrid mode
- History + ZIP export
- v0.1 retrieval pipeline: canonical artifacts, page-aware chunks, BM25 indexing, query traces
- Custom Next.js inspector UI (documents, query workbench, eval dashboard) via FastAPI
- Planner v1 routing with route settings, evidence consolidation, and trace diagnostics
- Graph retrieval mode for section/entity/reference expansion with query diagnostics
- Persisted `knowledge_graph.json` artifacts and cross-document graph search over shared entities/references
- Eval reports with planner-vs-static comparison metrics

## Progress Snapshot (2026-05-03)

- Phase 6 structured knowledge layer is complete for the planned v0.3 scope.
- Retrieval foundation is stable across `bm25`, `dense`, `late`, `hybrid`, `visual`, `graph`, and `planner` modes.
- Graph retrieval now traverses section/entity/reference links and emits diagnostics in retrieval traces.
- Multi-document graph querying is available through corpus search and eval manifests via `document_ids`.
- Planner mode is now the default query path across CLI/API/core retrieval, and routes multi-document graph-intent queries through corpus-level graph traversal.
- Planner mode supports `score_max` and `route_vote` merge strategies plus optional query-overlap reranking.
- Eval can sweep planner merge/rerank variants and report best variants by MRR/confidence.
- Planner defaults now favor the MRR-leading sweep variant: `score_max` merge with soft query-overlap reranking.
- Latest 10-document fixture validation: planner MRR `0.736`, term hit `1.000`, citation support `1.000`, answerable `1.000`.
- Latest sweep winner remains `score_rerank_soft` by MRR, with `route_vote_rerank_strong` retained as a confidence-oriented experiment.
- Planner route-vote and overlap-rerank weights are tunable, with large-manifest templates under `datasets/manifests/`.
- A reproducible weak-OCR visual fixture now validates visual retrieval quality and planner visual contribution diagnostics (`scripts/build_visual_phase4_fixture.py`).
- Query and eval UI surfaces graph diagnostics, and document pages expose filterable knowledge-graph artifacts.
- Query and eval UI now surface visual diagnostics (visual steps/hits and planner visual contribution rate).
- Graph extraction recognizes acronym definitions, quoted concepts, section aliases, numeric ranges, and DOI/arXiv/URL references.
- Graph extraction now normalizes common OCR reference noise (for example `Sectlon`, `F1gure`, `Tab1e`, `arX1v`, `Tabie`, `arxlv`) before reference parsing.
- Eval reports summarize graph extraction counts and optional expected entity/reference/section recall.
- Eval graph extraction summary now supports quality-tier drift reporting via `document_quality_tiers` and `expected_*_by_tier`.
- Fixture graph extraction recall is currently `1.000` for expected entities, references, and sections across 10 generated documents.
- A reproducible planner tuning fixture can generate a local sweep manifest under `data/generated/`.
- Knowledge cards include confidence, answerability reason, unresolved ambiguity notes, and follow-up retrieval suggestions.
- `knowledge_graph.json` is now persisted per document and exposed via API document detail responses.

## Quick Start

```bash
ollama pull glm-ocr
pip install -r requirements.txt
# Add GEMINI_API_KEY to .env
streamlit run streamlit_app.py
# or
python gradio_app.py
```

## Custom UI (Next.js + FastAPI)

The custom UI is now the primary direction. Streamlit and Gradio remain available during migration.

Backend API:

```bash
python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload
```

Frontend app:

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://localhost:3000` for the custom UI.

## Background Jobs

Long-running operations (ingest, chunk, index) can be submitted as background jobs via CLI or API:

```bash
# Start the worker in a separate terminal
python3 -m retrieval_research.cli worker

# Submit jobs asynchronously (CLI)
python3 -m retrieval_research.cli ingest large.pdf --async
python3 -m retrieval_research.cli chunk <document-id> --async
python3 -m retrieval_research.cli index <document-id> --async

# Check job status
python3 -m retrieval_research.cli jobs
python3 -m retrieval_research.cli job-status <job_id>
```

The API also exposes job endpoints:

```bash
# Ingest returns immediately with a job_id by default
curl -X POST -F "file=@doc.pdf" http://localhost:8000/api/documents/ingest

# Check status
curl http://localhost:8000/api/jobs/<job_id>

# List all jobs
curl http://localhost:8000/api/jobs

# Use ?sync=true for synchronous execution (backward compat)
curl -X POST -F "file=@doc.pdf" http://localhost:8000/api/documents/ingest?sync=true
```

The `--store` flag configures the artifact root (default: `$RR_DATA_ROOT` or `data/`). Job storage uses `RR_JOBS_ROOT` (default: `data/jobs/`).

## Visual Broad Benchmark

A diverse visual benchmark evaluates page retrieval across 6 synthetic document types:

| Fixture | Layout Type | Description |
|---------|------------|-------------|
| `dense_table` | Rich data table | 9-row company table with revenue, growth, employees |
| `application_form` | Form layout | Employment form with labeled fields and submit button |
| `text_with_figure` | Mixed text + diagram | Research article with embedded architecture figure |
| `bar_chart` | Chart visualization | Quarterly revenue bar chart by region |
| `pie_chart` | Chart visualization | Market share pie chart by vendor |
| `financial_metrics` | Sparse table | Key financial metrics with values and changes |

To build and run:

```bash
python3 scripts/build_visual_broad_benchmark.py
python3 -m retrieval_research.cli eval data/generated/visual_broad_benchmark_eval.json --modes visual planner
```

Current baseline: visual page_hit_rate=1.000, planner page_hit_rate=0.800 on 10 queries across 6 fixture documents.

## Retrieval v0.1 CLI

The CLI stores artifacts under `data/` and can ingest text/Markdown, prior history JSON, images, and PDFs. Image/PDF OCR is opt-in because local OCR model startup is expensive.

```bash
python3 -m retrieval_research.cli ingest README.md
python3 -m retrieval_research.cli chunk <document-id>
python3 -m retrieval_research.cli index <document-id> --mode all
python3 -m retrieval_research.cli query "retrieval pipeline" --mode planner
python3 -m retrieval_research.cli eval datasets/manifests/readme_eval.example.json
```

Eval manifests can use either `document_id` or `document_ids` for multi-document graph benchmarks.
For graph extraction drift analysis, manifests can also define `document_quality_tiers` and optional `expected_entities_by_tier`, `expected_references_by_tier`, and `expected_sections_by_tier`.

To rebuild the local planner tuning fixture and run the current sweep baseline:

```bash
python3 scripts/build_planner_tuning_fixture.py
python3 -m retrieval_research.cli eval data/generated/planner_tuning_sweep.local.json --modes bm25 dense late hybrid graph planner --planner-sweep
```

To build and validate the weak-OCR visual Phase 4 fixture:

```bash
python3 scripts/build_visual_phase4_fixture.py
python3 -m retrieval_research.cli eval data/generated/phase4_visual_eval.local.json --modes visual planner
```

Retrieval modes now include `bm25`, `dense`, `late`, `hybrid`, `visual`, `graph`, and `planner`. The `late` mode is a dependency-free ColBERT-style MaxSim baseline.

Supported retrieval query modes:

- `bm25`
- `dense`
- `late`
- `hybrid`
- `visual`
- `graph`
- `planner`

Quick sanity check after indexing:

```bash
python3 -m retrieval_research.cli query "what is this document about?" --mode planner --top-k 3
```

For PDFs/images with OCR:

```bash
python3 -m retrieval_research.cli ingest path/to/file.pdf --ocr --mode Hybrid --dpi 150
```

For real visual page retrieval with ColPali, install the optional runtime and rebuild the visual index:

```bash
pip install colpali-engine torch
python3 -m retrieval_research.cli index <document-id> --mode visual --visual-backend colpali --visual-compression int8 --device auto
python3 -m retrieval_research.cli query "what does the diagram show?" --document-id <document-id> --mode visual
```

The default visual backend remains `baseline` so the project runs without GPU/model downloads. `--visual-compression int8` enables the first HPC-ColPali-style storage optimization path for ColPali page embeddings.

Generated query runs include:

- `data/runs/<run-id>/evidence_bundle.json`
- `data/runs/<run-id>/knowledge_card.json`
- `data/runs/<run-id>/retrieval_trace.json`
- `data/runs/<run-id>/eval_report.json`
- `data/runs/<run-id>/eval_report.md`

Knowledge cards include answerability, confidence, unresolved ambiguity notes, and follow-up retrieval suggestions.

See `IMPLEMENTATION_PLAN.md` for the phased build plan.
