import tempfile
import unittest
import time
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from retrieval_research.api import create_app
from retrieval_research.chunking import chunk_document
from retrieval_research.ingest import ingest_path
from retrieval_research.storage import ArtifactStore


@unittest.skipIf(TestClient is None, "fastapi test client unavailable")
class ApiTest(unittest.TestCase):
    def test_health_endpoint_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            health_res = client.get("/api/health")
            self.assertEqual(health_res.status_code, 200)
            self.assertEqual(health_res.json()["status"], "ok")
            self.assertEqual(health_res.json()["service"], "retrieval-research-api")
            self.assertEqual(health_res.json()["version"], "0.1.0")

    def test_document_and_query_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api_sample.md"
            source.write_text(
                "# API Retrieval\n\nThis corpus contains keyword retrieval and semantic retrieval text.\n",
                encoding="utf-8",
            )
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)
            store = ArtifactStore(str(root / "data"))

            document = ingest_path(str(source), store=store)
            chunks = chunk_document(document, max_words=30, overlap_words=5)
            store.save_chunks(document.id, chunks)

            documents_res = client.get("/api/documents")
            self.assertEqual(documents_res.status_code, 200)
            self.assertEqual(documents_res.json()["documents"][0]["id"], document.id)

            detail_res = client.get(f"/api/documents/{document.id}")
            self.assertEqual(detail_res.status_code, 200)
            self.assertEqual(detail_res.json()["stats"]["chunk_count"], len(chunks))

            index_res = client.post(
                f"/api/documents/{document.id}/index",
                json={"mode": "all", "visual_backend": "baseline", "visual_compression": "none"},
            )
            self.assertEqual(index_res.status_code, 200)
            indexed_detail_res = client.get(f"/api/documents/{document.id}")
            self.assertEqual(indexed_detail_res.status_code, 200)
            self.assertIn("knowledge_graph", indexed_detail_res.json()["stats"])
            self.assertGreaterEqual(indexed_detail_res.json()["stats"]["knowledge_graph"]["node_count"], 1)

            query_res = client.post(
                "/api/query",
                json={"question": "keyword retrieval", "document_id": document.id, "mode": "hybrid", "top_k": 3},
            )
            self.assertEqual(query_res.status_code, 200)
            payload = query_res.json()
            self.assertIn("run_id", payload)
            self.assertTrue(payload["result"]["knowledge_card"]["answerable"])

            runs_res = client.get("/api/runs")
            self.assertEqual(runs_res.status_code, 200)
            run_id = payload["run_id"]
            self.assertIn(run_id, [run["id"] for run in runs_res.json()["runs"]])

            run_detail = client.get(f"/api/runs/{run_id}")
            self.assertEqual(run_detail.status_code, 200)
            self.assertIn("evidence_bundle.json", run_detail.json()["files"])

            eval_manifest = {
                "document_id": document.id,
                "queries": [{"query": "keyword retrieval", "expected_terms": ["keyword"], "expected_pages": [1]}],
            }
            eval_res = client.post("/api/eval", json={"manifest": eval_manifest, "top_k": 3, "modes": ["hybrid"]})
            self.assertEqual(eval_res.status_code, 200)
            self.assertEqual(eval_res.json()["report"]["metrics"]["modes"]["hybrid"]["query_count"], 1)

    def test_ingest_upload_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            upload_res = client.post(
                "/api/documents/ingest",
                files={"file": ("upload.md", b"# Upload\n\nUpload endpoint body.", "text/markdown")},
                data={"ocr": "false", "mode": "Hybrid", "dpi": "150"},
            )
            self.assertEqual(upload_res.status_code, 200)
            document_id = upload_res.json()["document_id"]

            detail_res = client.get(f"/api/documents/{document_id}")
            self.assertEqual(detail_res.status_code, 200)

    def test_documents_are_listed_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)
            store = ArtifactStore(str(root / "data"))

            first = root / "first.md"
            first.write_text("# First\n\nAlpha", encoding="utf-8")
            second = root / "second.md"
            second.write_text("# Second\n\nBeta", encoding="utf-8")

            first_doc = ingest_path(str(first), store=store)
            time.sleep(0.01)
            second_doc = ingest_path(str(second), store=store)

            documents_res = client.get("/api/documents")
            self.assertEqual(documents_res.status_code, 200)
            ids = [item["id"] for item in documents_res.json()["documents"]]
            self.assertEqual(ids[:2], [second_doc.id, first_doc.id])

    def test_query_endpoint_rejects_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            query_res = client.post(
                "/api/query",
                json={"question": "test", "mode": "unknown_mode"},
            )
            self.assertEqual(query_res.status_code, 400)
            self.assertIn("Unsupported retrieval mode", query_res.json()["detail"])

    def test_query_endpoint_validates_top_k(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            query_res = client.post(
                "/api/query",
                json={"question": "test", "mode": "hybrid", "top_k": 0},
            )
            self.assertEqual(query_res.status_code, 422)

    def test_query_endpoint_rejects_empty_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            query_res = client.post(
                "/api/query",
                json={"question": "test", "mode": "hybrid", "top_k": 3},
            )
            self.assertEqual(query_res.status_code, 400)
            self.assertIn("No documents available", query_res.json()["detail"])

    def test_index_endpoint_rejects_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "index_sample.md"
            source.write_text("# Index\n\nMode validation sample.", encoding="utf-8")
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)
            store = ArtifactStore(str(root / "data"))

            document = ingest_path(str(source), store=store)
            chunk_document(document, max_words=30, overlap_words=5)

            index_res = client.post(
                f"/api/documents/{document.id}/index",
                json={"mode": "not_a_mode"},
            )
            self.assertEqual(index_res.status_code, 400)
            self.assertIn("Unsupported index mode", index_res.json()["detail"])

    def test_query_endpoint_rejects_unknown_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(store_root=str(root / "data"))
            client = TestClient(app)

            query_res = client.post(
                "/api/query",
                json={"question": "test", "mode": "hybrid", "document_id": "missing-doc"},
            )
            self.assertEqual(query_res.status_code, 404)
            self.assertIn("Document not found", query_res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
