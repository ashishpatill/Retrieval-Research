from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from retrieval_research.config import get_settings
from retrieval_research.log import get_logger
from .models import Job, JobStatus, JobType, _now

_logger = get_logger("jobs.store")


class JobStore:
    def __init__(self, root: str | None = None):
        resolved = root if root is not None else get_settings().jobs_root
        self.root = Path(resolved)
        self.root.mkdir(parents=True, exist_ok=True)

    def _job_path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def submit(self, type: JobType, params: Dict[str, Any]) -> Job:
        job = Job(
            job_id=f"{type.value}_{_now()}",
            type=type,
            created_at=_now(),
            params=params,
        )
        self._save(job)
        _logger.info("Job submitted: %s (%s)", job.job_id, type.value)
        return job

    def _save(self, job: Job) -> None:
        self._job_path(job.job_id).write_text(
            json.dumps(job.to_dict(), indent=2), encoding="utf-8"
        )

    def load(self, job_id: str) -> Optional[Job]:
        path = self._job_path(job_id)
        if not path.exists():
            return None
        return Job.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 50) -> List[Job]:
        jobs = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            if len(jobs) >= limit:
                break
            try:
                job = Job.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError) as exc:
                _logger.warning("Corrupt job file %s: %s", path.name, exc)
                continue
            if status is None or job.status == status:
                jobs.append(job)
        return jobs

    def claim_next(self) -> Optional[Job]:
        for job in reversed(self.list_jobs(status=JobStatus.PENDING)):
            job.status = JobStatus.RUNNING
            job.started_at = _now()
            self._save(job)
            return job
        return None

    def complete(self, job_id: str, result: Dict[str, Any]) -> None:
        job = self.load(job_id)
        if job is None:
            _logger.warning("Cannot complete unknown job: %s", job_id)
            return
        job.status = JobStatus.SUCCEEDED
        job.completed_at = _now()
        job.result = result
        self._save(job)

    def fail(self, job_id: str, error: str) -> None:
        job = self.load(job_id)
        if job is None:
            _logger.warning("Cannot fail unknown job: %s", job_id)
            return
        job.status = JobStatus.FAILED
        job.completed_at = _now()
        job.error = error
        self._save(job)
