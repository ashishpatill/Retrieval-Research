# Hybrid Retrieval

Hybrid Retrieval blends lexical BM25 and dense semantic search. It is strong when a query combines exact tokens with paraphrased intent, for example "planner route settings" or "semantic summary behavior." Hybrid retrieval should be the everyday baseline for text-heavy documents.

# Graph Retrieval

Graph Retrieval behaves differently. It starts from ranked chunks and expands through document structure. It can recover related sections when the top lexical result is incomplete, especially for cross-document questions about shared entities and references.

## Comparison

Hybrid retrieval optimizes direct relevance. Graph retrieval optimizes context expansion. Planner mode decides which behavior to use, then records the route decision and merge strategy in the retrieval trace.
