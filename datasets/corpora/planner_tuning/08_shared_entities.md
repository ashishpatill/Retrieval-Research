# Shared Entities

Shared Entities allow corpus graph search to connect related documents. If one document defines Retrieval Planner and another describes Route Vote, the entity graph can provide cross-document evidence when both mention planner routing.

Entity extraction should recognize acronyms, quoted concepts, and section aliases. For example, Retrieval Augmented Generation (RAG), "cross-document routing", Knowledge Graph, and Score Max should become searchable anchors.

## Sections And References

Section aliases help when a query asks "which section explains graph expansion." References help when the corpus mentions Figure 2, Table 1, Section 3, arXiv:2401.12345, DOI 10.1234/example, or knowledge_graph.json.
