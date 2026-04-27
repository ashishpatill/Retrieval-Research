import tempfile
import unittest
import json
from pathlib import Path

from retrieval_research.chunking import chunk_document
from retrieval_research.evaluation import run_eval
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
            chunks = chunk_document(loaded, max_words=20, overlap_words=2)
            store.save_chunks(document.id, chunks)
            index = BM25Index(chunks)
            dense_index = DenseIndex(chunks)
            build_indexes(store, document.id, mode="all")
            hits = index.search("keyword retrieval", top_k=3)
            dense_hits = dense_index.search("semantic matches", top_k=3)
            hybrid_hits, hybrid_steps = search_document(store, document.id, "keyword retrieval", mode="hybrid", top_k=3)
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

            self.assertEqual(loaded.id, document.id)
            self.assertGreaterEqual(len(chunks), 1)
            self.assertGreaterEqual(len(hits), 1)
            self.assertGreaterEqual(len(dense_hits), 1)
            self.assertGreaterEqual(len(hybrid_hits), 1)
            self.assertGreaterEqual(len(visual_hits), 1)
            self.assertGreaterEqual(len(planner_hits), 1)
            self.assertEqual(hybrid_steps[-1]["path"], "hybrid")
            self.assertEqual(visual_steps[-1]["path"], "visual")
            self.assertEqual(plan.query_type, "visual")
            self.assertEqual(planner_steps[0]["path"], "planner")
            self.assertEqual(hits[0].document_id, document.id)
            self.assertEqual(report["metrics"]["modes"]["bm25"]["query_count"], 1)
            self.assertEqual(report["metrics"]["modes"]["hybrid"]["term_hit_rate"], 1.0)

    def test_colpali_optional_dependency_message(self):
        try:
            _load_runtime()
        except ColPaliUnavailableError as exc:
            self.assertIn("colpali-engine", str(exc))


if __name__ == "__main__":
    unittest.main()
