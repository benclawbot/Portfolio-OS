import json
import time

import pytest

from portfolio_os.operations import RefreshOperations


def test_records_immutable_runs_and_latest(tmp_path):
    operations = RefreshOperations(tmp_path)
    first = {"status": "completed", "completed_at_epoch": 1000.0, "duration_seconds": 1.2, "stages": []}
    second = {"status": "failed", "completed_at_epoch": 1001.0, "duration_seconds": 2.0, "stages": []}
    first_path = operations.record_run(first)
    second_path = operations.record_run(second)
    assert first_path.exists()
    assert second_path.exists()
    assert first_path != second_path
    latest = json.loads(operations.latest_path.read_text(encoding="utf-8"))
    assert latest["status"] == "failed"
    assert [run["status"] for run in operations.list_runs()] == ["failed", "completed"]


def test_run_limit_is_applied(tmp_path):
    operations = RefreshOperations(tmp_path)
    for index in range(3):
        operations.record_run({"status": "completed", "completed_at_epoch": 1000.0 + index, "stages": []})
    assert len(operations.list_runs(limit=2)) == 2


def test_lock_status_detects_missing_and_stale(tmp_path):
    operations = RefreshOperations(tmp_path)
    assert operations.inspect_lock().exists is False
    operations.lock_path.write_text(json.dumps({"pid": 1, "started_at_epoch": time.time() - 7200}), encoding="utf-8")
    status = operations.inspect_lock(stale_after_seconds=3600)
    assert status.exists is True
    assert status.stale is True
    assert status.malformed is False


def test_malformed_lock_is_stale(tmp_path):
    operations = RefreshOperations(tmp_path)
    operations.lock_path.write_text("bad", encoding="utf-8")
    status = operations.inspect_lock()
    assert status.stale is True
    assert status.malformed is True


def test_live_lock_cannot_be_cleared(tmp_path):
    operations = RefreshOperations(tmp_path)
    operations.lock_path.write_text(json.dumps({"pid": 1, "started_at_epoch": time.time()}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not stale"):
        operations.clear_stale_lock(stale_after_seconds=3600)


def test_stale_lock_can_be_explicitly_cleared(tmp_path):
    operations = RefreshOperations(tmp_path)
    operations.lock_path.write_text(json.dumps({"pid": 1, "started_at_epoch": 1}), encoding="utf-8")
    status = operations.clear_stale_lock(stale_after_seconds=1)
    assert status.stale is True
    assert not operations.lock_path.exists()
