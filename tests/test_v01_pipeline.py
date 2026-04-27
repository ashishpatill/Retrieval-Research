import tempfile
import unittest
import json
from pathlib import Path

from retrieval_research.chunking import chunk_document
from retrieval_research.evidence import build_knowledge_card
from retrieval_research.evaluation import run_eval
from retrieval_research.evaluation.runner import _has_supported_citations
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import (
    BM25Index,
    ColPaliUnavailableError,
    DenseIndex,
    build_indexes,
    plan_query,
    search_document,
)
from retrieval_research.retrieval.colpali import _load_runtime
from retrieval_research.storage import ArtifactStore


class V01PipelineTest(unittest.TestCase):
    def test_text_ingest_chunk_retrieve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.md"
            source.write_text(
                "# Retrieval Notes\n\nBM25 is useful for exact keyword retrieval.\n"
                "Dense retrieval helps with semantic matches.\n",
                encoding="utf-8",
            )
            store = ArtifactStore(str(root / "data"))
            document = ingest_path(str(source), store=store)
            loaded = store.load_document(document.id)
            profile = store.load_document_profile(document.id)
            chunks = chunk_document(loaded, max_words=20, overlap_words=2)
            store.save_chunks(document.id, chunks)
            index = BM25Index(chunks)
            dense_index = DenseIndex(chunks)
            build_indexes(store, document.id, mode="all")
            hits = index.search("keyword retrieval", top_k=3)
            dense_hits = dense_index.search("semantic matches", top_k=3)
            hybrid_hits, hybrid_steps = search_document(store, document.id, "keyword retrieval", mode="hybrid", top_k=3)
            knowledge_card = build_knowledge_card("keyword retrieval", hybrid_hits)
            visual_hits, visual_steps = search_document(store, document.id, "figure on the page", mode="visual", top_k=3)
            planner_hits, planner_steps = search_document(store, document.id, "figure on the page", mode="planner", top_k=3)
            plan = plan_query("figure on the page")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "document_id": document.id,
                        "queries": [
                            {
                                "query": "keyword retrieval",
                                "expected_terms": ["keyword", "retrieval"],
                                "expected_pages": [1],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_eval(str(manifest), store=store, top_k=3)
            store.save_run("eval_run", "eval_report.json", report)
            store.save_run("query_run", "retrieval_trace.json", {"steps": []})
            runs = store.list_runs()
            loaded_report = store.load_run("eval_run", "eval_report.json")

            self.assertEqual(loaded.id, document.id)
            self.assertEqual(profile.document_id, document.id)
            self.assertEqual(profile.page_count, 1)
            self.assertGreater(profile.total_words, 0)
            self.assertIn("Retrieval Notes", profile.headings)
            self.assertGreaterEqual(len(chunks), 1)
            self.assertGreaterEqual(len(hits), 1)
            self.assertGreaterEqual(len(dense_hits), 1)
            self.assertGreaterEqual(len(hybrid_hits), 1)
            self.assertTrue(knowledge_card.answerable)
            self.assertGreater(knowledge_card.confidence, 0.0)
            self.assertIn("Evidence confidence", knowledge_card.answerability_reason)
            self.assertIn(hybrid_hits[0].chunk_id, knowledge_card.answer)
            self.assertEqual(knowledge_card.claims[0].citation_ids, ["C1"])
            self.assertGreaterEqual(len(visual_hits), 1)
            self.assertGreaterEqual(len(planner_hits), 1)
            self.assertEqual(hybrid_steps[-1]["path"], "hybrid")
            self.assertEqual(visual_steps[-1]["path"], "visual")
            self.assertEqual(plan.query_type, "visual")
            self.assertEqual(planner_steps[0]["path"], "planner")
            self.assertIn("route_settings", planner_steps[0])
            planner_route_steps = [step for step in planner_steps if step["path"] == "planner_route"]
            self.assertGreaterEqual(len(planner_route_steps), 1)
            self.assertIn("route_top_k", planner_route_steps[0])
            planner_merge = next(step for step in planner_steps if step["path"] == "planner_merge")
            self.assertIn("redundancy_groups", planner_merge)
            self.assertIn("conflicts_detected", planner_merge)
            self.assertEqual(planner_merge["requested_top_k"], 3)
            self.assertEqual(planner_merge["merge_strategy"], "score_max")
            self.assertGreaterEqual(planner_merge["unique_chunks"], planner_merge["hits"])
            self.assertIn("source_paths", planner_hits[0].metadata)
            self.assertEqual(hits[0].document_id, document.id)
            self.assertEqual(report["metrics"]["modes"]["bm25"]["query_count"], 1)
            self.assertEqual(report["metrics"]["modes"]["hybrid"]["term_hit_rate"], 1.0)
            self.assertEqual(report["metrics"]["modes"]["hybrid"]["citation_support_rate"], 1.0)
            self.assertEqual(report["metrics"]["modes"]["hybrid"]["answerable_rate"], 1.0)
            self.assertIn("knowledge_card", report["results"][0])
            self.assertEqual(loaded_report["top_k"], 3)
            self.assertIn("eval_report.json", next(run["files"] for run in runs if run["id"] == "eval_run"))

    def test_colpali_optional_dependency_message(self):
        try:
            _load_runtime()
        except ColPaliUnavailableError as exc:
            self.assertIn("colpali-engine", str(exc))

    def test_empty_claim_citations_are_not_supported(self):
        card = {
            "answerable": True,
            "citations": [{"id": "C1"}],
            "claims": [{"text": "unsupported claim", "citation_ids": []}],
        }

        self.assertFalse(_has_supported_citations(card))


if __name__ == "__main__":
    unittest.main()
