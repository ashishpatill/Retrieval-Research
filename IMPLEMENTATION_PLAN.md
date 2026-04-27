# Implementation Plan

This plan turns `retrieval_roadmap.md` into an implementation sequence for the project. It intentionally ignores the research paper roadmap for now and focuses on shipping a usable retrieval/document-intelligence system from the current codebase.

## Progress status (session checkpoint)

Last updated: 2026-04-28

Current milestone: **v0.3 (in progress)**

Completed:

- Phase 0 foundation:
  - Canonical schema + artifact store under `data/`.
  - Ingestion pipeline and CLI entrypoints.
  - Package structure + smoke tests.
- Phase 1 text retrieval baseline:
  - Page-aware chunking.
  - BM25 + dense retrieval + hybrid fusion.
  - Query traces and evidence bundles.
- Phase 2 evaluation harness:
  - Eval manifest execution via CLI/API.
  - Mode metrics, citation support, answerability and confidence reporting.
- Phase 3 inspector UI:
  - Custom Next.js UI scaffold in `apps/web`.
  - Document library, document detail workspace, query workbench, eval page.
  - FastAPI backend surface in `retrieval_research/api.py`.
- Phase 5 planner and adaptive routing (partial):
  - Query classifier and rule-based route selection.
  - Route-specific planner settings (top-k factors and merge strategy) recorded in traces.
  - Evidence consolidation with redundancy/conflict annotations in `planner_merge`.
  - Confidence + answerability estimates added to knowledge cards and eval outputs.

In progress / remaining for near-term roadmap:

- Phase 4 completion:
  - Broaden visual retrieval quality and benchmark on image/table-heavy corpora.
- Phase 5 completion:
  - Compare planner-routed retrieval against static modes with explicit benchmark reports.
  - Improve merge strategy controls (e.g., alternative merge policies and rerank toggles).
- Phase 6 start:
  - Graph-style retrieval path (section/entity/reference traversal).
  - Richer `knowledge_card.json` fields for unresolved ambiguity and follow-up retrieval suggestions.

Next session start point:

1. Add planner-vs-static comparison report generation in eval output (phase 5 remaining).
2. Add a first graph retrieval stub/path to begin phase 6.
3. Expose these new outputs in `/evals` and `/query` custom UI pages.

## Current baseline

The repository currently contains a working document parsing prototype:

- `core_processor.py`: page preprocessing, GLM-OCR via MLX, optional Gemini refinement.
- `streamlit_app.py`: upload/process/history UI.
- `gradio_app.py`: alternate batch-processing UI.
- `history/`: JSON output from prior runs.

This is closest to the roadmap's ingestion layer. The missing product layers are canonical document storage, chunking, indexes, retrieval, evidence bundles, evaluation, and a retrieval-oriented inspector UI.

## Target v0 product

Build a local-first hard-document retrieval system that can:

1. Ingest PDFs/images and preserve page-level provenance.
2. Normalize OCR/refined output into a canonical document schema.
3. Chunk documents with page, section, layout, and confidence metadata.
4. Index chunks in lexical and dense retrieval backends.
5. Answer queries with grounded evidence and retrieval traces.
6. Evaluate retrieval and answer quality on a small reproducible corpus.
7. Expose the workflow through a practical inspector UI.

## Phase 0: Stabilize the Foundation

Goal: Convert the parser prototype into reusable project modules with testable data contracts.

Deliverables:

- Create package structure:
  - `retrieval_research/ingest/`
  - `retrieval_research/schema/`
  - `retrieval_research/storage/`
  - `retrieval_research/chunking/`
  - `retrieval_research/retrieval/`
  - `retrieval_research/evidence/`
  - `retrieval_research/evaluation/`
- Move OCR/page processing out of top-level app coupling.
- Define canonical schema models:
  - `Document`
  - `Page`
  - `Block`
  - `Table`
  - `Figure`
  - `Chunk`
  - `Evidence`
  - `RetrievalTrace`
- Replace ad hoc history JSON with versioned artifacts under `data/`:
  - `data/raw/`
  - `data/pages/`
  - `data/processed/`
  - `data/indexes/`
  - `data/runs/`
- Add CLI entrypoints:
  - `rr ingest <path>`
  - `rr chunk <document-id>`
  - `rr index <document-id>`
  - `rr query "<question>"`
  - `rr eval <manifest>`
- Add smoke tests for schema serialization and one-page ingestion.

Acceptance criteria:

- Existing Streamlit and Gradio flows still work.
- A processed document can be saved and loaded without losing page provenance.
- One command can ingest a PDF/image into canonical JSON.

## Phase 1: Strong Text Retrieval Baseline

Goal: Ship a reliable text-first RAG baseline before adding multimodal retrieval.

Deliverables:

- Implement chunking:
  - fixed-size baseline chunker
  - section-aware chunker using Markdown headings from OCR/refinement output
  - page-aware chunk boundaries with source coordinates reserved in the schema
- Implement lexical retrieval:
  - start with local BM25, such as `rank-bm25` or Tantivy/Pyserini later
  - persist index metadata under `data/indexes/`
- Implement dense retrieval:
  - local embedding model adapter
  - FAISS or Qdrant adapter
  - model-agnostic embedding interface
- Implement hybrid fusion:
  - weighted score fusion
  - reciprocal rank fusion
- Implement answer generation:
  - query retrieves evidence chunks
  - Gemini or configurable LLM produces grounded answer
  - answer includes citations to document/page/chunk
- Emit `retrieval_trace.json` and `evidence_bundle.json` for every query.

Acceptance criteria:

- Querying over ingested documents returns ranked chunks and an answer.
- Evidence includes source file, page number, chunk id, retrieval scores, and text.
- BM25-only, dense-only, and hybrid modes are selectable.

## Phase 2: Evaluation Harness

Goal: Make retrieval quality measurable from the start.

Deliverables:

- Define manifest format for eval corpora:
  - document paths
  - questions
  - expected answer snippets
  - expected pages/chunks when known
- Add metrics:
  - Recall@k
  - MRR
  - page hit rate
  - citation support rate
  - answerability flag
  - latency per stage
- Add small seed eval set:
  - one research paper
  - one report
  - one scanned or image-heavy document
  - one table/form-heavy document
- Add eval command that writes run reports to `data/runs/`.

Acceptance criteria:

- `rr eval` produces JSON and Markdown reports.
- Reports compare BM25, dense, and hybrid retrieval.
- Latency and quality metrics are captured for each query.

## Phase 3: Inspector UI

Goal: Turn the app from a parser into a retrieval debugging workbench.

Deliverables:

- Update Streamlit first, keeping Gradio as a secondary interface.
- Add document library view:
  - uploaded documents
  - processing status
  - page count
  - chunk count
  - index status
- Add query workbench:
  - query input
  - retrieval mode selector
  - answer panel
  - ranked evidence panel
  - retrieval trace panel
- Add page/evidence viewer:
  - show page image when available
  - highlight page/chunk provenance where coordinates exist
  - expose raw OCR and refined text side by side
- Add eval dashboard:
  - latest run summary
  - per-query pass/fail details
  - retrieval mode comparison

Acceptance criteria:

- A user can ingest, index, query, and inspect evidence from the UI.
- Every answer has visible evidence and a trace.
- Failed or low-confidence answers are easy to diagnose.

## Phase 4: Multimodal Page Retrieval

Goal: Add the roadmap's visual retrieval path after the text baseline is stable.

Deliverables:

- Persist page images during ingestion.
- Add visual retriever interface:
  - page encoder
  - query encoder
  - page-level ranking
- Integrate ColPali-compatible retrieval as the first visual backend.
- Add visual evidence objects:
  - page id
  - thumbnail path
  - visual score
  - linked text chunks from the same page
- Fuse visual and text retrieval results.
- Add multimodal retrieval mode to CLI and UI.

Acceptance criteria:

- Visually dense pages can be retrieved even when OCR text is weak.
- Query traces show when visual retrieval contributed evidence.
- Evaluation reports include page hit rate for visual retrieval.

## Phase 5: Planner and Adaptive Routing

Goal: Replace static retrieval mode selection with rule-based routing, then prepare for learned routing.

Deliverables:

- Implement query classifier:
  - exact lookup
  - semantic question
  - table/form lookup
  - visual/layout question
  - multi-hop synthesis
- Implement rule-based planner:
  - chooses BM25/dense/hybrid/visual paths
  - chooses top-k and reranking settings
  - records decisions in `retrieval_trace.json`
- Add evidence consolidation:
  - deduplicate overlapping chunks
  - merge page-level visual hits with text chunks
  - annotate conflicts and redundancy
- Add confidence and answerability estimates.

Acceptance criteria:

- Default query mode is planner-routed retrieval.
- Trace explains the route and why it was selected.
- Planner can be evaluated against static retrieval modes.

## Phase 6: Structured Knowledge Layer

Goal: Add graph-style document navigation and structured communication objects.

Deliverables:

- Extract section hierarchy into a navigable graph.
- Extract lightweight entities and references from refined text.
- Add graph traversal retrieval path for:
  - section expansion
  - citation/reference chase
  - entity neighborhood lookup
- Produce `knowledge_card.json`:
  - answer
  - claims
  - supporting evidence
  - unresolved ambiguity
  - suggested follow-up retrieval
- Produce `document_profile.json`:
  - topics
  - entities
  - page types
  - table/figure inventory
  - extraction confidence summary

Acceptance criteria:

- Retrieval can expand from a hit chunk to sibling/parent/child sections.
- Final answers can be exported as structured knowledge cards.
- Corpus/document profiles are visible in the UI.

## Phase 7: Hardening and Packaging

Goal: Make the project reliable for external contributors and repeated local use.

Deliverables:

- Add configuration system:
  - models
  - storage paths
  - retrieval backends
  - API keys
  - GPU/CPU options
- Add background jobs for ingestion/indexing.
- Add structured logging.
- Add error handling for missing models, failed OCR, failed API calls, and corrupt PDFs.
- Add Docker/devcontainer path if feasible.
- Expand tests:
  - schema tests
  - chunking tests
  - retrieval tests
  - CLI smoke tests
  - UI smoke tests
- Update README with real workflows.

Acceptance criteria:

- New users can run the project from README instructions.
- Core CLI commands work in a clean environment.
- The app degrades gracefully when optional cloud/model dependencies are unavailable.

## Suggested implementation order

1. Refactor `core_processor.py` into package modules while preserving current app behavior.
2. Add canonical schemas and artifact storage.
3. Add ingestion CLI.
4. Add chunking and local BM25 retrieval.
5. Add dense embeddings and hybrid retrieval.
6. Add grounded QA with evidence bundles and traces.
7. Add evaluation manifests and metrics.
8. Upgrade Streamlit into the retrieval inspector.
9. Add visual page retrieval.
10. Add planner routing and evidence consolidation.
11. Add graph/knowledge-card layer.
12. Harden packaging, configuration, and tests.

## Near-term milestone: v0.1

Scope:

- Canonical schema.
- File-backed artifact store.
- PDF/image ingestion CLI.
- Page-aware chunking.
- BM25 retrieval.
- Streamlit query page.
- Evidence bundle and retrieval trace.
- Minimal eval manifest with one sample document.

Definition of done:

- From a fresh document, a user can run ingest, chunk, index, query, and inspect evidence.
- No multimodal page retrieval yet.
- No paper/research experiment work.
- No distributed services yet.

## Near-term milestone: v0.2

Scope:

- Dense retrieval.
- Hybrid fusion.
- Grounded QA.
- Expanded eval harness.
- Document library in UI.
- Better OCR/refinement artifact tracking.

Definition of done:

- Hybrid retrieval beats BM25-only on the seed eval set.
- Every answer includes page/chunk citations.
- Eval reports are generated automatically.

## Near-term milestone: v0.3

Scope:

- Persisted page images.
- ColPali-compatible visual page retrieval adapter.
- Visual evidence in UI.
- Planner v1 with rule-based query routing.

Definition of done:

- Visual retrieval improves page hit rate on image-heavy/table-heavy docs.
- Query traces show selected retrieval paths and evidence fusion.

## Deferred for now

These remain in the roadmap but are not needed to complete the first implementation:

- Research paper writing.
- Large ablation suite.
- Rust hot-path optimization.
- Distributed service decomposition.
- HPC-ColPali compression work.
- Learned MoE chunk router.
- Learned planner model.
- Public benchmark release.