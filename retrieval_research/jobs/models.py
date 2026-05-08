from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobType(str, Enum):
    INGEST = "ingest"
    CHUNK = "chunk"
    INDEX = "index"
    PIPELINE = "pipeline"


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


@dataclass
class Job:
    job_id: str
    type: JobType
    status: JobStatus = JobStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "type": self.type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "params": self.params,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> Job:
        return cls(
            job_id=payload["job_id"],
            type=JobType(payload["type"]),
            status=JobStatus(payload.get("status", "pending")),
            created_at=payload.get("created_at", ""),
            started_at=payload.get("started_at", ""),
            completed_at=payload.get("completed_at", ""),
            params=payload.get("params", {}),
            result=payload.get("result", {}),
            error=payload.get("error", ""),
        )
