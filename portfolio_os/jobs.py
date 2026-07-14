from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class JobRecord:
    id: str
    kind: str
    status: str
    created_at: str
    updated_at: str
    parameters: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobQueue:
    """Durable, dependency-free job queue for local Portfolio OS services."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.root = self.workspace / "jobs"
        self.pending = self.root / "pending"
        self.running = self.root / "running"
        self.completed = self.root / "completed"
        self.failed = self.root / "failed"

    def submit(self, kind: str, parameters: dict[str, Any] | None = None) -> JobRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = JobRecord(
            id=uuid.uuid4().hex,
            kind=kind,
            status="pending",
            created_at=now,
            updated_at=now,
            parameters=parameters or {},
        )
        self._write(self.pending / f"{record.id}.json", record.to_dict())
        return record

    def get(self, job_id: str) -> JobRecord | None:
        for directory in (self.pending, self.running, self.completed, self.failed):
            path = directory / f"{job_id}.json"
            if path.exists():
                return self._load(path)
        return None

    def list(self, status: str | None = None) -> list[JobRecord]:
        directories = {
            "pending": self.pending,
            "running": self.running,
            "completed": self.completed,
            "failed": self.failed,
        }
        selected = [directories[status]] if status in directories else list(directories.values())
        records = [self._load(path) for directory in selected for path in sorted(directory.glob("*.json"))]
        return sorted(records, key=lambda item: (item.created_at, item.id), reverse=True)

    def run_next(self, handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]) -> JobRecord | None:
        self.pending.mkdir(parents=True, exist_ok=True)
        pending = sorted(self.pending.glob("*.json"), key=lambda path: path.stat().st_mtime)
        if not pending:
            return None
        source = pending[0]
        record = self._load(source)
        running_path = self.running / source.name
        running = self._replace(record, status="running")
        self._move(source, running_path, running.to_dict())
        try:
            handler = handlers[record.kind]
            result = handler(record.parameters)
            completed = self._replace(running, status="completed", result=result)
            self._move(running_path, self.completed / source.name, completed.to_dict())
            return completed
        except Exception as error:
            failed = self._replace(running, status="failed", error=f"{type(error).__name__}: {error}")
            self._move(running_path, self.failed / source.name, failed.to_dict())
            return failed

    @staticmethod
    def _replace(
        record: JobRecord,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> JobRecord:
        return JobRecord(
            id=record.id,
            kind=record.kind,
            status=status,
            created_at=record.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            parameters=record.parameters,
            result=result,
            error=error,
        )

    @staticmethod
    def _load(path: Path) -> JobRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return JobRecord(**payload)

    @staticmethod
    def _move(source: Path, destination: Path, payload: dict[str, Any]) -> None:
        JobQueue._write(destination, payload)
        source.unlink(missing_ok=True)

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
