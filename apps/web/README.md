# Retrieval Inspector Web UI

This app is the Next.js inspector frontend for the retrieval research backend.

## Current Scope

- Document library and document detail views
- Query workbench with retrieval trace inspection
- Eval runner with report rendering
- Graph retrieval diagnostics in query and eval views
- Document-level knowledge graph stats in the detail page

## Progress Snapshot (2026-05-03)

- Phase 6 inspector updates are complete for graph/profile diagnostics.
- Query workbench surfaces graph diagnostics (seed/expanded stats and relation summaries).
- Query workbench can filter graph evidence by expanded relation.
- Query and eval forms expose planner merge strategy and query-overlap rerank controls.
- Query and eval forms default to the current planner setting: `score_max` merge with query-overlap reranking enabled at weight `0.10`.
- Query and eval forms now default eval modes to include `visual` and `graph` so multimodal diagnostics are visible by default.
- Eval runner can benchmark all planner merge/rerank variants and summarize the best variants.
- Query and eval forms expose route-vote bonus and overlap-rerank weight controls for tuning.
- Query workbench now includes visual diagnostics with evidence profile metadata (`image_path`, inferred visual profile tokens).
- Knowledge cards now display unresolved ambiguity notes and follow-up retrieval suggestions.
- Eval runner includes aggregate graph diagnostics and per-query graph trace snippets.
- Eval runner also includes visual diagnostics (`visual_step_count`, `visual_hit_count`, planner visual contribution rate).
- Eval runner summarizes graph extraction counts and expected entity/reference/section recall.
- Document detail page shows graph index readiness plus filterable sections, entities, references, and relation counts.
- Document profile panel now surfaces structured reference inventory with in-panel filtering and per-kind copy actions.

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
