# Graph Expansion

Graph Retrieval expands from a seed chunk to related chunks through sections, shared entities, references, and neighboring chunks. This is most useful when the query asks for cross-document context or asks which section explains a concept.

The Knowledge Graph stores section nodes, entity nodes, and reference nodes. Shared Entities connect documents that mention the same concept, such as Retrieval Planner, Knowledge Graph, Graph Expansion, or Hybrid Retrieval. Reference links point to section names, table mentions, DOI identifiers, URLs, and artifacts like knowledge_graph.json.

## Cross-Document Context

Cross-document graph traversal can bridge a planner tuning note with an evaluation note when both discuss route_vote, overlap rerank, or citation support.
