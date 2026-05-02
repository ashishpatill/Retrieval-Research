# Planner Sweep

An evaluation manifest can request a Planner Sweep by defining variants. Each variant names a merge strategy, a rerank flag, a route vote bonus, and an overlap weight. The runner reports every variant and highlights best_by_mrr and best_by_confidence.

The default manifest should include cross-document synthesis, graph reference lookup, exact lookup, visual routing, and table-heavy retrieval. This mix prevents tuning only for one easy category.

## Sweep Variants

score_base uses score_max without rerank. score_rerank_soft enables overlap rerank with a small weight. route_vote_mid applies route_vote. route_vote_rerank_mid and route_vote_rerank_strong combine voting with reranking.

The current product default follows score_rerank_soft: score_max merge with query-overlap reranking at weight 0.10. Route-vote variants remain useful for checking whether confidence improves without masking weak evidence.
