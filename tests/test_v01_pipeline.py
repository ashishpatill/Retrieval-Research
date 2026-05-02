import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image, ImageDraw

from retrieval_research.cli import build_parser
from retrieval_research.chunking import chunk_document
from retrieval_research.evidence import build_knowledge_card
from retrieval_research.evaluation import run_eval
from retrieval_research.evaluation.runner import _has_supported_citations
from retrieval_research.ingest import ingest_path
from retrieval_research.retrieval import (
    BM25Index,
    ColPaliUnavailableError,
    DEFAULT_PLANNER_RERANK,
    DEFAULT_RERANK_OVERLAP_WEIGHT,
    DenseIndex,
    GraphIndex,
    LateInteractionIndex,
    build_indexes,
    plan_query,
    search_corpus,
    search_document,
)
from retrieval_research.retrieval.colpali import _load_runtime
from retrieval_research.retrieval.compression import dequantize_int8, quantize_int8
from retrieval_research.retrieval.graph import _references
from retrieval_research.retrieval.service import _consolidate_planner_hits
from retrieval_research.profiling import build_document_profile
from retrieval_research.schema import Chunk, Document, DocumentProfile, Evidence, Page
from retrieval_research.storage import ArtifactStore


class V01PipelineTest(unittest.TestCase):
    @staticmethod
    def _draw_table_image(path: Path) -> None:
        image = Image.new("RGB", (900, 600), "white")
        draw = ImageDraw.Draw(image)
        for x in range(80, 860, 120):
            draw.line((x, 80, x, 540), fill="black", width=4)
        for y in range(80, 560, 70):
            draw.line((80, y, 860, y), fill="black", width=4)
        image.save(path, format="PNG")

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
            self.assertEqual(planner_merge["reranked"], DEFAULT_PLANNER_RERANK)
            self.assertEqual(planner_merge["rerank_overlap_weight"], DEFAULT_RERANK_OVERLAP_WEIGHT)
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
            self.assertEqual(report["planner"]["rerank"], DEFAULT_PLANNER_RERANK)
            self.assertIn("knowledge_card", report["results"][0])
            self.assertEqual(loaded_report["top_k"], 3)
            self.assertIn("eval_report.json", next(run["files"] for run in runs if run["id"] == "eval_run"))

    def test_visual_mode_handles_weak_ocr_fixture_and_reports_visual_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "table.png"
            self._draw_table_image(image_path)
            store = ArtifactStore(str(root / "data"))
            document = ingest_path(str(image_path), store=store, run_ocr=False)
            chunks = chunk_document(document, max_words=30, overlap_words=0)
            store.save_chunks(document.id, chunks)
            build_indexes(store, document.id, mode="all")

            visual_hits, visual_steps = search_document(
                store,
                document.id,
                "table with rows and columns",
                mode="visual",
                top_k=3,
            )
            planner_hits, planner_steps = search_document(
                store,
                document.id,
                "visual table layout page image",
                mode="planner",
                top_k=3,
            )
            manifest = root / "visual_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "document_id": document.id,
                        "queries": [
                            {
                                "query": "table with rows and columns",
                                "expected_pages": [1],
                                "expected_terms": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_eval(str(manifest), store=store, top_k=3, modes=["visual", "planner"])

            self.assertGreaterEqual(len(visual_hits), 1)
            self.assertEqual(visual_steps[-1]["path"], "visual")
            self.assertIn("visual_profile", visual_hits[0].metadata)
            self.assertGreater(len(visual_hits[0].metadata["visual_profile"]), 0)
            self.assertTrue(any(step["path"] == "planner_merge" for step in planner_steps))
            self.assertTrue(any("visual" in hit.metadata.get("source_paths", []) for hit in planner_hits))
            self.assertIn("visual", report["metrics"]["modes"])
            self.assertGreater(report["metrics"]["modes"]["visual"]["page_hit_rate"], 0.0)
            visual_diag = report["metrics"]["visual_diagnostics"]
            self.assertTrue(visual_diag["available"])
            self.assertGreaterEqual(visual_diag["visual_step_count"], 1)

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

            self.assertIn("Alpha Section", {chunk.parent_section for chunk in chunks})
            self.assertIn("Beta", {chunk.parent_section for chunk in chunks})
            self.assertEqual(graph_artifact["type"], "knowledge_graph")
            self.assertGreater(graph_artifact["stats"]["entity_count"], 0)
            self.assertGreater(graph_artifact["stats"]["reference_count"], 0)
            self.assertGreater(relation_counts.get("same_entity", 0), 0)
            self.assertGreater(relation_counts.get("reference", 0), 0)
            self.assertGreaterEqual(len(hits), 1)
            self.assertTrue(any("same_entity" in hit.metadata["graph_relations"] or "reference" in hit.metadata["graph_relations"] for hit in hits))
            self.assertGreater(steps[-1]["diagnostics"]["edge_count"], 0)

    def test_graph_section_navigation_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sections.md"
            source.write_text(
                "# 2 Methods\n\nIntro methods body.\n\n"
                "# 2.1 Setup\n\nSetup details body.\n\n"
                "# 3 Results\n\nResults body.\n",
                encoding="utf-8",
            )
            store = ArtifactStore(str(root / "data"))
            document = ingest_path(str(source), store=store)
            chunks = chunk_document(document, max_words=8, overlap_words=0)
            store.save_chunks(document.id, chunks)
            build_indexes(store, document.id, mode="graph")

            graph_payload = store.load_index(document.id, "graph")
            relation_counts = graph_payload["stats"]["relation_counts"]
            self.assertGreater(relation_counts.get("next_section", 0), 0)
            self.assertGreater(relation_counts.get("previous_section", 0), 0)
            self.assertGreater(relation_counts.get("child_section", 0), 0)
            self.assertGreater(relation_counts.get("parent_section", 0), 0)

    def test_document_profile_structured_reference_inventory(self):
        document = Document(
            id="doc-inv",
            source_path="inv.md",
            title="Inventory",
            pages=[
                Page(
                    id="p1",
                    number=1,
                    text="See Figure 1, Tab1e 2, and arX1v:1234.5678 for Section Alpha.",
                )
            ],
        )
        profile = build_document_profile(document)
        inv = profile.structured_reference_inventory
        self.assertIn("figure", inv)
        self.assertIn("figure:1", inv["figure"])
        self.assertIn("table", inv)
        self.assertIn("table:2", inv["table"])
        self.assertIn("arxiv", inv)
        self.assertTrue(any(r.startswith("arxiv:") for r in inv["arxiv"]))
        self.assertIn("section", inv)

    def test_document_profile_from_dict_tolerates_legacy_and_extra_keys(self):
        payload = {
            "document_id": "legacy",
            "title": "Legacy",
            "source_type": "md",
            "page_count": 1,
            "text_page_count": 1,
            "image_page_count": 0,
            "total_words": 5,
            "page_types": {"text": 1},
            "unknown_future_key": {"x": 1},
        }
        profile = DocumentProfile.from_dict(payload)
        self.assertEqual(profile.document_id, "legacy")
        self.assertEqual(profile.structured_reference_inventory, {})
        self.assertEqual(profile.headings, [])

    def test_planner_merge_strategy_and_rerank_controls(self):
        hits = [
            Evidence(
                chunk_id="a",
                document_id="doc",
                page_numbers=[1],
                text="background material",
                score=0.9,
                retrieval_path="bm25",
            ),
            Evidence(
                chunk_id="b",
                document_id="doc",
                page_numbers=[2],
                text="alpha beta focused answer",
                score=0.86,
                retrieval_path="bm25",
            ),
            Evidence(
                chunk_id="b",
                document_id="doc",
                page_numbers=[2],
                text="alpha beta focused answer",
                score=0.84,
                retrieval_path="dense",
            ),
        ]

        score_max_hits, score_max_stats = _consolidate_planner_hits(
            hits,
            top_k=1,
            query_type="semantic",
            planner_reason="test",
            query="alpha beta",
            merge_strategy="score_max",
            rerank=False,
        )
        route_vote_hits, route_vote_stats = _consolidate_planner_hits(
            hits,
            top_k=1,
            query_type="semantic",
            planner_reason="test",
            query="alpha beta",
            merge_strategy="route_vote",
            rerank=False,
        )
        reranked_hits, reranked_stats = _consolidate_planner_hits(
            hits,
            top_k=1,
            query_type="semantic",
            planner_reason="test",
            query="alpha beta",
            merge_strategy="score_max",
            rerank=True,
        )

        self.assertEqual(score_max_hits[0].chunk_id, "a")
        self.assertEqual(route_vote_hits[0].chunk_id, "b")
        self.assertEqual(reranked_hits[0].chunk_id, "b")
        self.assertFalse(score_max_stats["reranked"])
        self.assertFalse(route_vote_stats["reranked"])
        self.assertTrue(reranked_stats["reranked"])
        self.assertEqual(route_vote_hits[0].metadata["merge_strategy"], "route_vote")
        self.assertTrue(reranked_hits[0].metadata["reranked"])

    def test_graph_extraction_handles_acronyms_aliases_and_external_refs(self):
        chunks = [
            Chunk(
                id="doc:chunk:0",
                document_id="doc",
                page_numbers=[1],
                text=(
                    "Background cites Section 2.1, Figures 1 and 2, DOI 10.1234/ABC.DEF, "
                    "and arXiv: 2401.12345. The method is Retrieval Augmented Generation "
                    "(RAG) with `cross-document routing`."
                ),
                chunk_index=0,
                parent_section="Background",
            ),
            Chunk(
                id="doc:chunk:1",
                document_id="doc",
                page_numbers=[2],
                text="The 2.1 Retrieval Planner section explains RAG and cross-document routing.",
                chunk_index=1,
                parent_section="2.1 Retrieval Planner",
            ),
            Chunk(
                id="doc:chunk:2",
                document_id="doc",
                page_numbers=[3],
                text="Figure 2 shows the RAG routing architecture.",
                chunk_index=2,
                parent_section="Figures",
            ),
        ]

        index = GraphIndex(chunks)
        graph = index.knowledge_graph
        references = {item["reference"] for item in graph["references"]}
        entities = {item["name"] for item in graph["entities"]}
        hits = index.search("Section 2.1 RAG Figure 2", top_k=5)

        self.assertIn("RAG", entities)
        self.assertIn("Retrieval Augmented Generation", entities)
        self.assertIn("cross-document routing", entities)
        self.assertIn("section:2.1", references)
        self.assertIn("figure:1", references)
        self.assertIn("figure:2", references)
        self.assertIn("doi:10.1234/abc.def", references)
        self.assertIn("arxiv:2401.12345", references)
        self.assertTrue(any(edge.get("reference") == "section:2.1" for edge in index.edges["doc:chunk:0"]))
        self.assertTrue(any(edge.get("reference") == "figure:2" for edge in index.edges["doc:chunk:0"]))
        self.assertTrue(any("reference" in hit.metadata["graph_relations"] for hit in hits))

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

            planner_hits, planner_steps = search_corpus(
                store,
                [first_doc.id, second_doc.id],
                "Acme Retrieval cross document routing",
                mode="planner",
                top_k=5,
            )
            planner_plan = plan_query("Acme Retrieval cross document routing")

            self.assertIn("graph", planner_plan.routes)
            self.assertEqual(planner_steps[0]["path"], "planner")
            self.assertEqual(planner_steps[0]["document_ids"], [first_doc.id, second_doc.id])
            self.assertTrue(any(step.get("route") == "graph" for step in planner_steps if step["path"] == "planner_route"))
            self.assertTrue(any(step.get("path") == "graph_corpus" for step in planner_steps))
            self.assertTrue(any(step.get("path") == "planner_merge" for step in planner_steps))
            self.assertEqual({hit.document_id for hit in planner_hits}, {first_doc.id, second_doc.id})

            manifest = root / "multi_doc_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "document_ids": [first_doc.id, second_doc.id],
                        "document_quality_tiers": {
                            first_doc.id: "clean",
                            second_doc.id: "noisy",
                        },
                        "expected_entities": ["Acme Retrieval"],
                        "expected_references": ["section:bridge"],
                        "expected_sections": ["Bridge"],
                        "expected_entities_by_tier": {
                            "clean": ["Acme Retrieval"],
                            "noisy": ["Acme Retrieval"],
                        },
                        "expected_references_by_tier": {
                            "clean": ["section:bridge"],
                            "noisy": ["section:bridge"],
                        },
                        "expected_sections_by_tier": {
                            "noisy": ["Bridge"],
                        },
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
            sweep_report = run_eval(str(manifest), store=store, top_k=5, modes=["planner"], planner_sweep=True)

            self.assertTrue(report["metrics"]["graph_diagnostics"]["available"])
            self.assertEqual(report["metrics"]["graph_diagnostics"]["max_document_count"], 2)
            graph_extraction = report["metrics"]["graph_extraction"]
            self.assertTrue(graph_extraction["available"])
            self.assertEqual(graph_extraction["document_count"], 2)
            self.assertEqual(graph_extraction["expected_recall"]["entities"]["recall"], 1.0)
            self.assertEqual(graph_extraction["expected_recall"]["references"]["recall"], 1.0)
            self.assertEqual(graph_extraction["expected_recall"]["sections"]["recall"], 1.0)
            by_tier = {item["quality_tier"]: item for item in graph_extraction["quality_tiers"]}
            self.assertEqual(set(by_tier), {"clean", "noisy"})
            self.assertEqual(by_tier["clean"]["document_count"], 1)
            self.assertEqual(by_tier["noisy"]["document_count"], 1)
            self.assertEqual(by_tier["clean"]["expected_recall"]["entities"]["recall"], 1.0)
            self.assertEqual(by_tier["noisy"]["expected_recall"]["sections"]["recall"], 1.0)
            self.assertEqual(report["results"][0]["document_ids"], [first_doc.id, second_doc.id])
            planner_sweep = sweep_report["metrics"]["planner_sweep"]
            self.assertTrue(planner_sweep["available"])
            self.assertEqual(len(planner_sweep["variants"]), 4)
            self.assertIn(planner_sweep["best_by_mrr"], {variant["name"] for variant in planner_sweep["variants"]})

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
        semantic_numeric_plan = plan_query("what happened in 2026 retrieval release")
        identifier_plan = plan_query("lookup ID AB-1234")

        self.assertEqual(visual_plan.query_type, "visual")
        self.assertIn("visual", visual_plan.routes)
        self.assertEqual(table_plan.query_type, "table_or_form")
        self.assertIn("late", table_plan.routes)
        self.assertEqual(semantic_numeric_plan.query_type, "semantic")
        self.assertEqual(identifier_plan.query_type, "exact_lookup")
        self.assertIn("route_explanation", visual_plan.to_dict())
        self.assertTrue(visual_plan.route_explanation)

    def test_cli_query_mode_defaults_to_planner(self):
        parser = build_parser()
        args = parser.parse_args(["query", "test query"])
        self.assertEqual(args.mode, "planner")

    def test_graph_reference_extraction_handles_ocr_like_noise(self):
        noisy = "Sectlon 2.1 and F1gure 3 plus Tab1e 2 with arX1v: 2401.12345 and DOI 10.1000/XYZ."
        refs = _references(noisy)
        self.assertIn("section:2.1", refs)
        self.assertIn("figure:3", refs)
        self.assertIn("table:2", refs)
        self.assertIn("arxiv:2401.12345", refs)
        self.assertIn("doi:10.1000/xyz", refs)

        noisy_alt = "SecTLon 4 cites F1G 5 and Tabie 7, plus arxlv:2402.54321."
        refs_alt = _references(noisy_alt)
        self.assertIn("section:4", refs_alt)
        self.assertIn("figure:5", refs_alt)
        self.assertIn("table:7", refs_alt)
        self.assertIn("arxiv:2402.54321", refs_alt)


if __name__ == "__main__":
    unittest.main()
