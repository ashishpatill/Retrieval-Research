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
    LateInteractionIndex,
    build_indexes,
    plan_query,
    search_corpus,
    search_document,
)
from retrieval_research.retrieval.colpali import _load_runtime
from retrieval_research.retrieval.compression import dequantize_int8, quantize_int8
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
            late_index = LateInteractionIndex(chunks)
            build_indexes(store, document.id, mode="all")
            hits = index.search("keyword retrieval", top_k=3)
            dense_hits = dense_index.search("semantic matches", top_k=3)
            late_hits = late_index.search("exact keyword retrieval", top_k=3)
            hybrid_hits, hybrid_steps = search_document(store, document.id, "keyword retrieval", mode="hybrid", top_k=3)
            service_late_hits, service_late_steps = search_document(store, document.id, "exact keyword retrieval", mode="late", top_k=3)
            knowledge_card = build_knowledge_card("keyword retrieval", hybrid_hits)
            visual_hits, visual_steps = search_document(store, document.id, "figure on the page", mode="visual", top_k=3)
            graph_hits, graph_steps = search_document(store, document.id, "related keyword retrieval context", mode="graph", top_k=3)
            planner_hits, planner_steps = search_document(store, document.id, "figure on the page", mode="planner", top_k=3)
            graph_plan_hits, graph_plan_steps = search_document(store, document.id, "related keyword retrieval context", mode="planner", top_k=3)
            plan = plan_query("figure on the page")
            graph_plan = plan_query("related keyword retrieval context")
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
            self.assertGreaterEqual(len(late_hits), 1)
            self.assertGreaterEqual(len(service_late_hits), 1)
            self.assertGreaterEqual(len(hybrid_hits), 1)
            self.assertTrue(knowledge_card.answerable)
            self.assertGreater(knowledge_card.confidence, 0.0)
            self.assertIn("Evidence confidence", knowledge_card.answerability_reason)
            self.assertIn("follow_up_retrieval_suggestions", knowledge_card.to_dict())
            self.assertIn(hybrid_hits[0].chunk_id, knowledge_card.answer)
            self.assertEqual(knowledge_card.claims[0].citation_ids, ["C1"])
            self.assertGreaterEqual(len(visual_hits), 1)
            self.assertGreaterEqual(len(graph_hits), 1)
            self.assertGreaterEqual(len(planner_hits), 1)
            self.assertGreaterEqual(len(graph_plan_hits), 1)
            self.assertEqual(hybrid_steps[-1]["path"], "hybrid")
            self.assertEqual(service_late_steps[-1]["path"], "late")
            self.assertEqual(visual_steps[-1]["path"], "visual")
            self.assertEqual(graph_steps[-1]["path"], "graph")
            self.assertEqual(graph_steps[-1]["expansion"], "section_entity_reference_graph")
            self.assertIn("diagnostics", graph_steps[-1])
            self.assertIn("graph_relations", graph_hits[0].metadata)
            self.assertEqual(plan.query_type, "visual")
            self.assertIn("graph", graph_plan.routes)
            self.assertTrue(any(step.get("route") == "graph" for step in graph_plan_steps if step["path"] == "planner_route"))
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
            self.assertEqual(list(report["metrics"]["modes"].keys()), sorted(report["metrics"]["modes"].keys()))
            planner_vs_static = report["metrics"]["planner_vs_static"]
            self.assertTrue(planner_vs_static["available"])
            self.assertIn("hybrid", planner_vs_static["baseline_modes"])
            self.assertEqual(planner_vs_static["baseline_modes"], sorted(planner_vs_static["baseline_modes"]))
            self.assertIn("delta_vs_baseline_avg", planner_vs_static)
            self.assertIn("knowledge_card", report["results"][0])
            self.assertEqual(loaded_report["top_k"], 3)
            self.assertIn("eval_report.json", next(run["files"] for run in runs if run["id"] == "eval_run"))

    def test_graph_index_builds_section_entity_and_reference_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "graph.md"
            source.write_text(
                "# Alpha Section\n\nAcme Retrieval describes Table 1 and cites Section Beta.\n\n"
                "# Beta\n\nAcme Retrieval details the entity relationship.\n\n"
                "# Tables\n\nTable 1 lists the retrieval metrics.\n",
                encoding="utf-8",
            )
            store = ArtifactStore(str(root / "data"))
            document = ingest_path(str(source), store=store)
            chunks = chunk_document(document, max_words=12, overlap_words=0)
            store.save_chunks(document.id, chunks)
            build_indexes(store, document.id, mode="graph")

            graph_payload = store.load_index(document.id, "graph")
            graph_artifact = store.load_knowledge_graph(document.id)
            relation_counts = graph_payload["stats"]["relation_counts"]
            hits, steps = search_document(store, document.id, "Acme Retrieval Section Beta Table 1", mode="graph", top_k=5)

            self.assertEqual(graph_artifact["type"], "knowledge_graph")
            self.assertGreater(graph_artifact["stats"]["entity_count"], 0)
            self.assertGreater(graph_artifact["stats"]["reference_count"], 0)
            self.assertGreater(relation_counts.get("same_entity", 0), 0)
            self.assertGreater(relation_counts.get("reference", 0), 0)
            self.assertGreaterEqual(len(hits), 1)
            self.assertTrue(any("same_entity" in hit.metadata["graph_relations"] or "reference" in hit.metadata["graph_relations"] for hit in hits))
            self.assertGreater(steps[-1]["diagnostics"]["edge_count"], 0)

    def test_corpus_graph_search_links_shared_entities_across_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_source = root / "alpha.md"
            second_source = root / "beta.md"
            first_source.write_text(
                "# Alpha\n\nAcme Retrieval introduces the planner architecture and cites Section Bridge.\n",
                encoding="utf-8",
            )
            second_source.write_text(
                "# Bridge\n\nAcme Retrieval describes cross document evidence routing.\n",
                encoding="utf-8",
            )
            store = ArtifactStore(str(root / "data"))
            first_doc = ingest_path(str(first_source), store=store)
            second_doc = ingest_path(str(second_source), store=store)
            for document in (first_doc, second_doc):
                chunks = chunk_document(document, max_words=20, overlap_words=0)
                store.save_chunks(document.id, chunks)
                build_indexes(store, document.id, mode="graph")

            hits, steps = search_corpus(
                store,
                [first_doc.id, second_doc.id],
                "Acme Retrieval cross document routing",
                mode="graph",
                top_k=5,
            )

            self.assertEqual(steps[-1]["path"], "graph_corpus")
            self.assertEqual(steps[-1]["diagnostics"]["document_count"], 2)
            self.assertGreater(steps[-1]["diagnostics"]["expanded_relation_counts"].get("same_entity", 0), 0)
            self.assertEqual({hit.document_id for hit in hits}, {first_doc.id, second_doc.id})

            manifest = root / "multi_doc_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "document_ids": [first_doc.id, second_doc.id],
                        "queries": [
                            {
                                "query": "Acme Retrieval cross document routing",
                                "expected_terms": ["routing"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_eval(str(manifest), store=store, top_k=5, modes=["graph"])

            self.assertTrue(report["metrics"]["graph_diagnostics"]["available"])
            self.assertEqual(report["metrics"]["graph_diagnostics"]["max_document_count"], 2)
            self.assertEqual(report["results"][0]["document_ids"], [first_doc.id, second_doc.id])

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

    def test_int8_embedding_compression_roundtrip(self):
        embedding = [[0.0, 0.5, -1.0], [1.0, -0.25, 0.125]]
        compressed = quantize_int8(embedding)
        restored = dequantize_int8(compressed)

        self.assertEqual(compressed["compression"], "int8")
        self.assertEqual(len(restored), 2)
        self.assertAlmostEqual(restored[0][1], 0.5, places=2)
        self.assertAlmostEqual(restored[0][2], -1.0, places=2)

    def test_planner_routes_plot_and_spreadsheet_queries(self):
        visual_plan = plan_query("show me the plot in this screenshot")
        table_plan = plan_query("find the spreadsheet total amount")

        self.assertEqual(visual_plan.query_type, "visual")
        self.assertIn("visual", visual_plan.routes)
        self.assertEqual(table_plan.query_type, "table_or_form")
        self.assertIn("late", table_plan.routes)


if __name__ == "__main__":
    unittest.main()
