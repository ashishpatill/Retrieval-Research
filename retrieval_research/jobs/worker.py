from __future__ import annotations

import signal
import sys
import time
from typing import Optional

from retrieval_research.config import get_settings
from retrieval_research.log import get_logger

from .handlers import handle_job
from .store import JobStore

_logger = get_logger("jobs.worker")

_shutdown = False


def _handle_signal(signum: int, _frame) -> None:
    global _shutdown
    _shutdown = True
    _logger.info("Shutdown signal received, finishing current job...")


def run_worker(poll_interval: Optional[float] = None) -> None:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if poll_interval is None:
        poll_interval = get_settings().job_poll_interval
    store = JobStore()
    _logger.info("Worker started (poll interval: %.1fs)", poll_interval)

    while not _shutdown:
        job = store.claim_next()
        if job is None:
            time.sleep(poll_interval)
            continue
        _logger.info("Processing job: %s (%s)", job.job_id, job.type.value)
        try:
            result = handle_job(job)
            store.complete(job.job_id, result)
            _logger.info("Job completed: %s", job.job_id)
        except Exception as exc:
            _logger.error("Job failed: %s — %s", job.job_id, exc)
            store.fail(job.job_id, str(exc))

    _logger.info("Worker stopped.")
    sys.exit(0)
