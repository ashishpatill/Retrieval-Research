# Retrieval Inspector Web UI

This app is the Next.js inspector frontend for the retrieval research backend.

## Current Scope

- Document library and document detail views
- Query workbench with retrieval trace inspection
- Eval runner with report rendering
- Graph retrieval diagnostics in query and eval views
- Document-level knowledge graph stats in the detail page

## Progress Snapshot (2026-05-01)

- Query workbench surfaces graph diagnostics (seed/expanded stats and relation summaries).
- Query workbench can filter graph evidence by expanded relation.
- Query and eval forms expose planner merge strategy and query-overlap rerank controls.
- Eval runner can benchmark all planner merge/rerank variants and summarize the best variants.
- Query and eval forms expose route-vote bonus and overlap-rerank weight controls for tuning.
- Knowledge cards now display unresolved ambiguity notes and follow-up retrieval suggestions.
- Eval runner includes aggregate graph diagnostics and per-query graph trace snippets.
- Eval runner summarizes graph extraction counts and expected entity/reference/section recall.
- Document detail page shows graph index readiness plus filterable sections, entities, references, and relation counts.

## Local Development

From this directory:

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Backend Requirement

Run the API server from repository root:

```bash
python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload
```
