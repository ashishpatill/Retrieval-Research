# Visual Retrieval

Visual Retrieval is reserved for page images, diagrams, forms, and table-heavy retrieval. In the baseline runtime, visual retrieval can still return page-level evidence, but production quality depends on a stronger page embedding backend.

Table-heavy documents often need both text and layout signals. A query such as "find the table that lists retrieval metrics" may start with BM25, but planner routing can include visual retrieval when the intent mentions a figure, form, page layout, or table.

## Routing Guidance

The planner should not route every table query through visual search. It should use visual routing when text evidence is sparse or when the user asks about what a diagram or page shows.
