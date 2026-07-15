import json
import subprocess

import pytest

from portfolio_os.execution import MedusaExecutionBridge
from portfolio_os.sync import RepositoryState, SyncState, save_state_atomic


class FakeRunner:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls = []

    def run(self, command, cwd):
        self.calls.append((command, cwd))
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, self.stderr)


def seed(tmp_path, *, dirty=False, archived=False, accessible=True):
    repository = tmp_path / "repositories" / "alpha"
    (repository / ".git").mkdir(parents=True)
    state = SyncState(
        owner="benclawbot",
        repositories={
            "1": RepositoryState(
                id=1,
                name="alpha",
                full_name="benclawbot/alpha",
                path=str(repository),
                default_branch="main",
                head_sha="abc",
                visibility="private",
                fork=False,
                archived=archived,
                updated_at="2026-07-15T00:00:00Z",
                status="unchanged",
                dirty=dirty,
                accessible=accessible,
            )
        },
    )
    save_state_atomic(state, tmp_path / "sync-state.json")
    backlog = tmp_path / "backlog" / "portfolio-backlog.json"
    backlog.parent.mkdir(parents=True)
    backlog.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "rec-123",
                        "title": "Fix release readiness",
                        "repository": "benclawbot/alpha",
                        "evidence": ["Checks are failing."],
                        "acceptance_criteria": ["Checks pass."],
                        "verification_plan": ["Run tests."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return repository


def test_accept_creates_bounded_durable_request(tmp_path):
    repository = seed(tmp_path)
    bridge = MedusaExecutionBridge(tmp_path)

    request = bridge.accept("rec-123")

    assert request.repository_path == str(repository.resolve())
    assert request.status == "accepted"
    assert "Work only inside this repository" in request.objective
    assert bridge.load_request(request.id) == request
    assert bridge.list_requests() == [request]


def test_execute_runs_medusa_and_records_verification_evidence(tmp_path):
    repository = seed(tmp_path)
    runner = FakeRunner(stdout="session 1 completed\nevidence: cargo test passed\nevidence: cargo clippy passed\n")
    bridge = MedusaExecutionBridge(tmp_path, medusa_binary="medusa-test", runner=runner)
    request = bridge.accept("rec-123")

    receipt = bridge.execute(request.id)

    assert runner.calls[0][0][:4] == ["medusa-test", "--repo", str(repository.resolve()), "run"]
    assert runner.calls[0][1] == repository.resolve()
    assert receipt.status == "completed"
    assert receipt.verification_evidence == ("cargo test passed", "cargo clippy passed")
    assert receipt.request_sha256
    assert bridge.list_receipts() == [receipt]


def test_failed_medusa_run_is_preserved_as_failed_receipt(tmp_path):
    seed(tmp_path)
    runner = FakeRunner(returncode=1, stderr="provider unavailable")
    bridge = MedusaExecutionBridge(tmp_path, runner=runner)
    request = bridge.accept("rec-123")

    receipt = bridge.execute(request.id)

    assert receipt.status == "failed"
    assert receipt.exit_code == 1
    assert receipt.stderr == "provider unavailable"


@pytest.mark.parametrize(
    ("dirty", "archived", "accessible", "message"),
    [
        (True, False, True, "dirty"),
        (False, True, True, "not executable"),
        (False, False, False, "not executable"),
    ],
)
def test_accept_rejects_unsafe_repository_states(tmp_path, dirty, archived, accessible, message):
    seed(tmp_path, dirty=dirty, archived=archived, accessible=accessible)
    bridge = MedusaExecutionBridge(tmp_path)

    with pytest.raises(ValueError, match=message):
        bridge.accept("rec-123")


def test_unknown_recommendation_or_request_fails(tmp_path):
    seed(tmp_path)
    bridge = MedusaExecutionBridge(tmp_path)

    with pytest.raises(KeyError):
        bridge.accept("rec-missing")
    with pytest.raises(KeyError):
        bridge.load_request("exec-missing")
