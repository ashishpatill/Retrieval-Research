<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python">
  <img src="https://img.shields.io/badge/next.js-16-black" alt="Next.js">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/tests-90%20passed-brightgreen" alt="Tests">
</p>

# Retrieval Research

**A retrieval engine that actually understands your documents.** Not just vector search over flattened text — this system ingests complex PDFs and images, builds seven parallel retrieval indexes (lexical, dense, late-interaction, visual, graph, hybrid, and planner-routed), and returns grounded answers with full provenance traces.

Standard RAG fails on real-world documents because it discards page structure, layout, tables, figures, and cross-references before retrieval even starts. This project keeps those signals alive and uses them.

---

## Why this exists

| Problem with standard RAG | What we do differently |
|---|---|
| Flattens everything to text chunks | Preserves pages, sections, entities, figures, tables, citations, and references as first-class objects |
| One retrieval method for all queries | Planner inspects the question and routes to the best index — BM25, dense, visual, graph, or any combination |
| No traceability | Every answer comes with `retrieval_trace.json`, `evidence_bundle.json`, and a `knowledge_card` with confidence and ambiguity notes |
| Multi-document reasoning is bolted on | Cross-document graph traversal connects shared entities and references across your entire corpus |
| PDFs with tables and diagrams break | Multimodal ingestion with OCR ensemble, layout preservation, and visual page indexing (ColPali-compatible) |

---

## Quick start

One command sets up everything:

```bash
./run-app.sh
```

Then in two terminals:

```bash
# Terminal 1 — backend API
source .venv/bin/activate
python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — web UI
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open **http://localhost:3000** and ingest a document.

> Optional: add `GEMINI_API_KEY` to `.env` for OCR refinement. The pipeline works without it — hybrid OCR mode uses local GLM-OCR via MLX and falls back gracefully.

---

## Architecture

```
  PDF / Image / Markdown
         │
         ▼
  ┌──────────────────────────────┐
  │   Ingestion & OCR Ensemble    │
  │   hybrid / pure-local / cloud │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │   Canonical Document Schema   │
  │   pages · sections · blocks   │
  │   tables · figures · refs     │
  └──────────┬───────────────────┘
             │
     ┌───────┼───────┬───────┬───────┐
     ▼       ▼       ▼       ▼       ▼
   bm25   dense   late    visual   graph
     │       │       │       │       │
     └───────┴───────┴───────┴───────┘
             │
             ▼
  ┌──────────────────────────────┐
  │       Query Planner           │
  │   inspects query → routes to  │
  │   best index combination      │
  └──────────┬───────────────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │   Evidence + Knowledge Card   │
  │   trace · citations · conf.   │
  └──────────────────────────────┘
```

---

## Retrieval modes

| Mode | When to use it | Backed by |
|---|---|---|
| `planner` | Default — adaptive routing based on query type | All indexes |
| `bm25` | Exact terms, IDs, codes, entity names | Lexical index |
| `dense` | Semantic similarity, broad topics | Embedding index |
| `late` | Fine-grained passage scoring, table/form queries | ColBERT-style MaxSim |
| `visual` | Diagrams, charts, layouts, scanned pages | Page-image index (baseline / ColPali) |
| `graph` | Cross-section navigation, entity linking, citation chase | Entity/reference/section graph |
| `hybrid` | Balanced recall across text modalities | BM25 + dense fusion |

### Planner intelligence

The planner classifies queries into **visual**, **table/form**, **graph/navigation**, **multi-hop**, **exact lookup**, or **semantic** categories using an expanded vocabulary with plural-stem normalization. A strong-identifier pre-check (DOI, version numbers, invoice codes, alphanumeric IDs) routes mixed-intent queries to exact lookup before content-based routing, fixing queries like "look up invoice INV-2024-001". It selects the optimal retrieval paths and records its reasoning in every trace. A 45+ query calibration test suite validates routing accuracy across all categories.

---

## CLI at a glance

```bash
# Ingest any document
rr ingest report.pdf --ocr --mode Hybrid

# Build chunks and indexes
rr chunk <doc-id>
rr index <doc-id> --mode all

# Query
rr query "what are the Q4 revenue figures?" --mode planner

# Evaluate a benchmark
rr eval datasets/manifests/readme_eval.example.json --modes bm25,dense,graph,planner

# Background jobs (async processing)
rr worker              # start the job worker
rr ingest large.pdf --async  # submit as a job
rr jobs                # list all jobs
```

---

## Web UI

<p align="center">
  <strong>Professional dark theme · shadcn-style components · lucide icons</strong>
</p>

- **Dashboard** — document count, eval runs, recent activity, one-click ingest
- **Documents** — browse, inspect page previews, view knowledge graphs, run chunk/index
- **Query** — full workbench with planner controls, mode selector, evidence panels, graph/visual diagnostics, raw trace inspection
- **Evals** — JSON manifest editor, multi-mode benchmark runner, planner sweep across merge/rerank variants, graph extraction quality reports

---

## What's under the hood

| Capability | Implementation |
|---|---|
| OCR | GLM-OCR (local MLX) + Gemini 3.1 Pro Preview (cloud) — ensemble with confidence routing |
| Chunking | Page-aware, section-preserving, configurable word/overlap windows |
| BM25 | In-house implementation with configurable k1/b parameters |
| Dense embedding | On-the-fly embedding with configurable dimensions |
| Late interaction | ColBERT-style MaxSim scoring — zero external dependencies |
| Visual retrieval | Baseline (layout/color profiles) + optional ColPali with int8 compression |
| Graph extraction | Regex-based entity, acronym, section, citation, DOI/arXiv/URL extraction with 60+ OCR noise patterns, numeric range expansion, and section hierarchy alias linking |
| Knowledge cards | Answerability, confidence, unresolved ambiguity, follow-up suggestions |
| Background jobs | File-based queue with `JobStore`, worker process, async API + CLI |
| Evaluation | Manifest-driven benchmarks with term hit, page hit, MRR, citation support, planner sweep, graph extraction recall, quality-tier drift reporting |

---

## Development

```bash
./run-app.sh          # one-time setup
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v   # 90 tests · < 2 seconds
```

The web frontend (`apps/web/`) is a standalone Next.js 16 project with Tailwind CSS v4 and shadcn-style UI primitives. Build it separately:

```bash
cd apps/web && npm run build
```

---

MIT License · built with Python, Next.js, and careful attention to document structure
