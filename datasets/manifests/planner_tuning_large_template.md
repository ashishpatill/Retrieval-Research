# Planner Tuning Large Manifest Template

Use this checklist to build a larger tuning manifest:

1. For a reproducible local smoke baseline, run `python3 scripts/build_planner_tuning_fixture.py`.
2. For a larger real benchmark, ingest and index at least 10-20 documents with mixed styles (narrative, table-heavy, citation-heavy, diagram-heavy).
3. Collect the resulting `document_id` values from the documents UI or `rr query` output.
4. Copy `planner_tuning_sweep.example.json` and replace `document_ids`.
5. Add 20-50 queries that cover:
   - exact lookup
   - semantic summaries
   - cross-document synthesis
   - graph/reference lookups
   - table/form retrieval
6. Fill `expected_terms`, and optionally `expected_entities`, `expected_references`, `expected_sections`.
7. Run:
   - `python3 -m retrieval_research.cli eval datasets/manifests/planner_tuning_sweep.example.json --modes planner --planner-sweep`
8. Compare sweep winners (`best_by_mrr`, `best_by_confidence`) against the current default.

Current fixture result: `score_rerank_soft` led by MRR without the confidence lift from route voting, so the default is `score_max` with query-overlap reranking enabled at `0.10`. Keep `route_vote_rerank_strong` as a confidence-oriented experiment until a larger mixed corpus justifies changing the default again.

Latest local fixture validation (`data/runs/20260503_013945_686187`) on 12 queries reported planner MRR `0.736`, term hit `1.000`, citation support `1.000`, and answerable `1.000`. Graph extraction quality on the same 10-document fixture reached expected entity/reference/section recall of `1.000`.

## Optional variant ideas

- Lower route-vote influence:
  - `route_vote_bonus`: `0.04`
- Strong route-vote influence:
  - `route_vote_bonus`: `0.12`
- Softer rerank:
  - `rerank_overlap_weight`: `0.08`
- Stronger rerank:
  - `rerank_overlap_weight`: `0.25`
