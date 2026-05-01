# Ambiguity Handling

Knowledge cards should expose unresolved ambiguity when evidence is incomplete or when several chunks answer different parts of the question. The card can add follow-up retrieval suggestions that ask for a narrower section, a specific document, or a graph expansion.

Ambiguity Handling matters for planner mode because route voting can make weak agreement look stronger than it is. If a query asks about "the routing method" without naming planner routing, visual routing, or graph routing, the answer should explain the ambiguity.

## Follow-Up Retrieval

Follow-up retrieval suggestions should point to the next useful action: search shared entities, inspect graph diagnostics, filter by section, or compare planner sweep variants.
