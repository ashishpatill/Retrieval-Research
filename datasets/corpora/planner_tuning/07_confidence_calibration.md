# Confidence Calibration

Confidence Calibration connects planner tuning to user trust. When evidence comes from several independent routes, confidence can increase. When evidence is redundant but thin, confidence should remain limited and the answerability reason should mention uncertainty.

The planner sweep should compare score_base, score_rerank_soft, route_vote_mid, route_vote_rerank_mid, and route_vote_rerank_strong. A useful default is the variant that improves MRR without inflating confidence on ambiguous questions.

## Calibration Checks

Review queries about route vote, graph expansion, citation support, and unresolved ambiguity. These query families reveal whether confidence follows evidence quality or just score magnitude.
