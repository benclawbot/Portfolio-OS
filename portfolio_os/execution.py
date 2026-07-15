from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from portfolio_os.sync import load_state


@dataclass(frozen=True)
class ExecutionRequest:
    schema_version: int
    id: str
    recommendation_id: str
    repository: str
    repository_path: str
    title: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    verification_plan: tuple[str, ...]
    evidence: tuple[str, ...]
    created_at: str
    status: str = "accepted"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionReceipt:
    schema_version: int
    request_id: str
    recommendation_id: str
    repository: str
    status: str
    started_at: str
    completed_at: str
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    verification_evidence: tuple[str, ...]
    request_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProcessRunner(Protocol):
    def run(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


class MedusaExecutionBridge:
    """Turn explicitly accepted recommendations into bounded Medusa executions."""

    def __init__(
        self,
        workspace: Path,
        *,
        medusa_binary: str = "medusa",
        runner: ProcessRunner | None = None,
    ) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.medusa_binary = medusa_binary
        self.runner = runner or SubprocessRunner()
        self.backlog_path = self.workspace / "backlog" / "portfolio-backlog.json"
        self.root = self.workspace / "execution"
        self.requests_dir = self.root / "requests"
        self.receipts_dir = self.root / "receipts"

    def accept(self, recommendation_id: str) -> ExecutionRequest:
        item = self._recommendation(recommendation_id)
        repository = str(item["repository"])
        repository_path = self._repository_path(repository)
        created_at = datetime.now(timezone.utc).isoformat()
        request_id = hashlib.sha256(
            f"{recommendation_id}|{repository}|{created_at}".encode("utf-8")
        ).hexdigest()[:20]
        request = ExecutionRequest(
            schema_version=1,
            id=f"exec-{request_id}",
            recommendation_id=recommendation_id,
            repository=repository,
            repository_path=str(repository_path),
            title=str(item["title"]),
            objective=self._objective(item),
            acceptance_criteria=tuple(str(value) for value in item.get("acceptance_criteria", [])),
            verification_plan=tuple(str(value) for value in item.get("verification_plan", [])),
            evidence=tuple(str(value) for value in item.get("evidence", [])),
            created_at=created_at,
        )
        self._write_json(self.requests_dir / f"{request.id}.json", request.to_dict())
        return request

    def execute(self, request_id: str) -> ExecutionReceipt:
        request = self.load_request(request_id)
        repository = Path(request.repository_path).expanduser().resolve()
        self._validate_repository(repository)
        request_path = self.requests_dir / f"{request.id}.json"
        request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()
        command = [self.medusa_binary, "--repo", str(repository), "run", request.objective]
        started_at = datetime.now(timezone.utc).isoformat()
        completed = self.runner.run(command, repository)
        completed_at = datetime.now(timezone.utc).isoformat()
        evidence = self._evidence(completed.stdout, completed.stderr)
        receipt = ExecutionReceipt(
            schema_version=1,
            request_id=request.id,
            recommendation_id=request.recommendation_id,
            repository=request.repository,
            status="completed" if completed.returncode == 0 else "failed",
            started_at=started_at,
            completed_at=completed_at,
            command=tuple(command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            verification_evidence=evidence,
            request_sha256=request_sha256,
        )
        self._write_json(self.receipts_dir / f"{request.id}.json", receipt.to_dict())
        return receipt

    def load_request(self, request_id: str) -> ExecutionRequest:
        path = self.requests_dir / f"{request_id}.json"
        if not path.exists():
            raise KeyError(request_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ExecutionRequest(
            **{
                **payload,
                "acceptance_criteria": tuple(payload.get("acceptance_criteria", [])),
                "verification_plan": tuple(payload.get("verification_plan", [])),
                "evidence": tuple(payload.get("evidence", [])),
            }
        )

    def list_requests(self) -> list[ExecutionRequest]:
        if not self.requests_dir.exists():
            return []
        return [self.load_request(path.stem) for path in sorted(self.requests_dir.glob("*.json"))]

    def list_receipts(self) -> list[ExecutionReceipt]:
        if not self.receipts_dir.exists():
            return []
        receipts = []
        for path in sorted(self.receipts_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            receipts.append(
                ExecutionReceipt(
                    **{
                        **payload,
                        "command": tuple(payload.get("command", [])),
                        "verification_evidence": tuple(payload.get("verification_evidence", [])),
                    }
                )
            )
        return receipts

    def _recommendation(self, recommendation_id: str) -> dict[str, Any]:
        if not self.backlog_path.exists():
            raise FileNotFoundError(f"backlog artifact not found: {self.backlog_path}")
        payload = json.loads(self.backlog_path.read_text(encoding="utf-8"))
        for item in payload.get("items", []):
            if isinstance(item, dict) and item.get("id") == recommendation_id:
                return item
        raise KeyError(recommendation_id)

    def _repository_path(self, full_name: str) -> Path:
        state = load_state(self.workspace / "sync-state.json")
        for repository in state.repositories.values():
            if repository.full_name == full_name:
                path = Path(repository.path).expanduser().resolve()
                self._validate_repository(path)
                if repository.dirty:
                    raise ValueError(f"repository checkout is dirty: {full_name}")
                if not repository.accessible or repository.archived:
                    raise ValueError(f"repository is not executable: {full_name}")
                return path
        raise KeyError(full_name)

    @staticmethod
    def _validate_repository(path: Path) -> None:
        if not path.is_dir() or not (path / ".git").exists():
            raise ValueError(f"managed repository is unavailable: {path}")

    @staticmethod
    def _objective(item: dict[str, Any]) -> str:
        acceptance = "\n".join(f"- {value}" for value in item.get("acceptance_criteria", []))
        verification = "\n".join(f"- {value}" for value in item.get("verification_plan", []))
        evidence = "\n".join(f"- {value}" for value in item.get("evidence", []))
        return (
            f"Implement Portfolio OS recommendation {item['id']}: {item['title']}\n\n"
            f"Evidence:\n{evidence or '- No additional evidence supplied.'}\n\n"
            f"Acceptance criteria:\n{acceptance or '- Complete the stated recommendation.'}\n\n"
            f"Verification plan:\n{verification or '- Run the repository test and quality gates.'}\n\n"
            "Work only inside this repository. Preserve unrelated user changes. "
            "Do not claim completion without explicit verification evidence."
        )

    @staticmethod
    def _evidence(stdout: str, stderr: str) -> tuple[str, ...]:
        lines = []
        for raw in (stdout + "\n" + stderr).splitlines():
            line = raw.strip()
            if line.lower().startswith("evidence:"):
                lines.append(line.split(":", 1)[1].strip())
        return tuple(dict.fromkeys(lines))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
