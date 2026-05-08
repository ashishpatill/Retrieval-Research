import json
import os
import tempfile
import unittest
from pathlib import Path

from retrieval_research.jobs import Job, JobStatus, JobType
from retrieval_research.jobs.store import JobStore


class JobModelTest(unittest.TestCase):
    def test_job_defaults(self):
        job = Job(job_id="test_001", type=JobType.INGEST)
        self.assertEqual(job.job_id, "test_001")
        self.assertEqual(job.type, JobType.INGEST)
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.params, {})
        self.assertEqual(job.result, {})
        self.assertEqual(job.error, "")
        self.assertEqual(job.created_at, "")
        self.assertEqual(job.started_at, "")
        self.assertEqual(job.completed_at, "")

    def test_job_roundtrip_dict(self):
        job = Job(
            job_id="rt_001",
            type=JobType.PIPELINE,
            status=JobStatus.RUNNING,
            created_at="20260509_120000_000000",
            started_at="20260509_120001_000000",
            params={"key": "value"},
        )
        d = job.to_dict()
        restored = Job.from_dict(d)
        self.assertEqual(restored.job_id, "rt_001")
        self.assertEqual(restored.type, JobType.PIPELINE)
        self.assertEqual(restored.status, JobStatus.RUNNING)
        self.assertEqual(restored.params, {"key": "value"})

    def test_job_status_enum_values(self):
        self.assertEqual(JobStatus.PENDING.value, "pending")
        self.assertEqual(JobStatus.RUNNING.value, "running")
        self.assertEqual(JobStatus.SUCCEEDED.value, "succeeded")
        self.assertEqual(JobStatus.FAILED.value, "failed")

    def test_job_type_enum_values(self):
        self.assertEqual(JobType.INGEST.value, "ingest")
        self.assertEqual(JobType.CHUNK.value, "chunk")
        self.assertEqual(JobType.INDEX.value, "index")
        self.assertEqual(JobType.PIPELINE.value, "pipeline")


class JobStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.store = JobStore(root=str(self.tmpdir))

    def tearDown(self):
        if self.tmpdir.exists():
            for path in self.tmpdir.rglob("*"):
                if path.is_file():
                    path.unlink()
            for path in reversed(list(self.tmpdir.rglob("*"))):
                if path.is_dir():
                    path.rmdir()
            self.tmpdir.rmdir()

    def test_submit_creates_job_file(self):
        job = self.store.submit(JobType.INGEST, {"path": "/tmp/test.pdf"})
        self.assertTrue(job.job_id.startswith("ingest_"))
        self.assertEqual(job.type, JobType.INGEST)
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.params, {"path": "/tmp/test.pdf"})
        job_path = self.tmpdir / f"{job.job_id}.json"
        self.assertTrue(job_path.exists())
        saved = json.loads(job_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["job_id"], job.job_id)
        self.assertEqual(saved["type"], "ingest")
        self.assertEqual(saved["status"], "pending")

    def test_load_returns_none_for_missing(self):
        self.assertIsNone(self.store.load("nonexistent"))

    def test_load_returns_job(self):
        submitted = self.store.submit(JobType.CHUNK, {"document_id": "doc_001"})
        loaded = self.store.load(submitted.job_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.job_id, submitted.job_id)
        self.assertEqual(loaded.params, {"document_id": "doc_001"})

    def test_list_jobs_returns_all(self):
        j1 = self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        j2 = self.store.submit(JobType.CHUNK, {"document_id": "doc_001"})
        jobs = self.store.list_jobs()
        job_ids = {j.job_id for j in jobs}
        self.assertIn(j1.job_id, job_ids)
        self.assertIn(j2.job_id, job_ids)

    def test_list_jobs_filters_by_status(self):
        self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        pending = self.store.list_jobs(status=JobStatus.PENDING)
        self.assertEqual(len(pending), 1)
        running = self.store.list_jobs(status=JobStatus.RUNNING)
        self.assertEqual(len(running), 0)

    def test_list_jobs_respects_limit(self):
        for i in range(5):
            self.store.submit(JobType.INGEST, {"path": f"{i}.pdf"})
        self.assertEqual(len(self.store.list_jobs(limit=3)), 3)
        self.assertEqual(len(self.store.list_jobs(limit=100)), 5)

    def test_claim_next_returns_pending_job(self):
        self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        claimed = self.store.claim_next()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, JobStatus.RUNNING)
        self.assertTrue(claimed.started_at)

    def test_claim_next_returns_none_when_empty(self):
        self.assertIsNone(self.store.claim_next())

    def test_claim_next_only_pending(self):
        j1 = self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        self.store.claim_next()
        self.assertIsNone(self.store.claim_next())
        loaded = self.store.load(j1.job_id)
        self.assertEqual(loaded.status, JobStatus.RUNNING)

    def test_complete_updates_job(self):
        job = self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        self.store.complete(job.job_id, {"document_id": "doc_001"})
        loaded = self.store.load(job.job_id)
        self.assertEqual(loaded.status, JobStatus.SUCCEEDED)
        self.assertEqual(loaded.result, {"document_id": "doc_001"})
        self.assertTrue(loaded.completed_at)

    def test_fail_updates_job(self):
        job = self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        self.store.fail(job.job_id, "something went wrong")
        loaded = self.store.load(job.job_id)
        self.assertEqual(loaded.status, JobStatus.FAILED)
        self.assertEqual(loaded.error, "something went wrong")
        self.assertTrue(loaded.completed_at)

    def test_complete_unknown_job_does_not_raise(self):
        self.store.complete("nonexistent", {})
        self.store.fail("nonexistent", "err")

    def test_claim_respects_fifo_order(self):
        j1 = self.store.submit(JobType.INGEST, {"path": "a.pdf"})
        j2 = self.store.submit(JobType.INGEST, {"path": "b.pdf"})
        claimed1 = self.store.claim_next()
        self.assertEqual(claimed1.job_id, j1.job_id)
        claimed2 = self.store.claim_next()
        self.assertEqual(claimed2.job_id, j2.job_id)


class JobTypeTest(unittest.TestCase):
    def test_all_types_have_handlers(self):
        from retrieval_research.jobs.handlers import handle_job
        for jtype in JobType:
            job = Job(job_id=f"test_{jtype.value}", type=jtype)
            with self.assertRaises((KeyError, ValueError, FileNotFoundError, OSError)):
                handle_job(job)


if __name__ == "__main__":
    unittest.main()
