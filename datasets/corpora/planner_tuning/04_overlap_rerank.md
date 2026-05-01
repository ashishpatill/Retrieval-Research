# Overlap Rerank

Overlap Rerank is a lightweight planner option that adds a small score adjustment when query tokens overlap with evidence text. The rerank_overlap_weight should stay modest because lexical overlap can over-reward repeated wording in boilerplate sections.

Soft rerank settings use an overlap weight near 0.10. Stronger rerank settings use a weight near 0.25 and should be tested against graph-heavy and exact-lookup questions. The sweep compares reranked variants with non-reranked variants so confidence and MRR can be reviewed together.

## Tuning Risk

If the overlap weight is too high, rerank can bury dense evidence that explains the concept but does not repeat the query wording.
