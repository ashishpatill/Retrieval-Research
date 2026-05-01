# Planner Routing

The Retrieval Planner selects routes for exact lookup, semantic summary, visual retrieval, and graph expansion. It records the chosen route settings in the trace so evaluation can explain why a query used BM25, dense, hybrid, visual, graph, or planner routing.

Route Vote is useful when the same chunk appears through several routes. A chunk that is retrieved by dense search and graph retrieval can receive a route_vote bonus because independent paths agree on its relevance. Score Max keeps the highest individual score and ignores the number of source paths.

## Merge Notes

Planner tuning compares route_vote with score_max merging. The expected behavior is conservative: route voting should help only when multiple routes converge on the same evidence, while score_max remains a stable baseline for single-route exact lookup.
