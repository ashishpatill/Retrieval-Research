# Evaluation Metrics

Planner tuning uses term hit rate, page hit rate, citation support, answerability, confidence, and MRR. Citation Support checks whether generated claims are grounded in cited evidence chunks. Answerability reports whether the knowledge card has enough evidence to answer the question.

Confidence Calibration is important because a route can return plausible evidence with weak support. A sweep variant should not be chosen only because average confidence rises. The report should compare MRR with confidence and inspect the hits that caused a change.

## Manifest Expectations

Evaluation manifests can include expected_terms, expected_pages, expected_entities, expected_sections, and expected_references. These fields make graph extraction quality visible in the report.
