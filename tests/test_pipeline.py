import json

import pytest

from portfolio_os.pipeline import PipelineLockedError, PortfolioPipeline


def seed_workspace(tmp_path):
    (tmp_path / "sync-state.json").write_text(
        json.dumps({"owner": "benclawbot", "synchronized_at": "", "repositories": {}}),
        encoding="utf-8",
    )


def test_runs_all_artifact_stages_without_sync(tmp_path):
    seed_workspace(tmp_path)

    result = PortfolioPipeline(tmp_path).run()

    assert result.status == "completed"
    assert [stage.status for stage in result.stages] == ["skipped", "completed", "completed", "completed"]
    assert (tmp_path / "portfolio" / "portfolio-summary.json").exists()
    assert (tmp_path / "history" / "latest.json").exists()
    assert (tmp_path / "trends" / "portfolio-trends.json").exists()
    assert (tmp_path / "dashboard" / "index.html").exists()
    assert (tmp_path / "pipeline" / "latest-run.json").exists()


def test_sync_stage_output_is_recorded(tmp_path):
    seed_workspace(tmp_path)
    pipeline = PortfolioPipeline(tmp_path, sync_stage=lambda: {"summary": {"repository_count": 0}})

    result = pipeline.run()

    assert result.stages[0].status == "completed"
    assert result.stages[0].output["summary"]["repository_count"] == 0


def test_failure_blocks_later_stages_by_default(tmp_path):
    def fail():
        raise RuntimeError("sync failed")

    result = PortfolioPipeline(tmp_path, sync_stage=fail).run()

    assert result.status == "failed"
    assert [stage.status for stage in result.stages] == ["failed", "blocked", "blocked", "blocked"]
    assert "RuntimeError: sync failed" == result.stages[0].error


def test_continue_on_error_attempts_independent_later_stages(tmp_path):
    seed_workspace(tmp_path)

    def fail():
        raise RuntimeError("sync failed")

    result = PortfolioPipeline(tmp_path, sync_stage=fail).run(continue_on_error=True)

    assert result.status == "failed"
    assert result.stages[0].status == "failed"
    assert [stage.status for stage in result.stages[1:]] == ["completed", "completed", "completed"]


def test_existing_lock_prevents_concurrent_refresh(tmp_path):
    seed_workspace(tmp_path)
    lock = tmp_path / ".portfolio-os-refresh.lock"
    lock.write_text("locked", encoding="utf-8")

    with pytest.raises(PipelineLockedError, match="another refresh"):
        PortfolioPipeline(tmp_path).run()


def test_lock_is_removed_after_failure(tmp_path):
    def fail():
        raise RuntimeError("boom")

    PortfolioPipeline(tmp_path, sync_stage=fail).run()

    assert not (tmp_path / ".portfolio-os-refresh.lock").exists()


def test_latest_run_is_valid_json(tmp_path):
    seed_workspace(tmp_path)
    pipeline = PortfolioPipeline(tmp_path)
    result = pipeline.run()
    saved = json.loads(pipeline.result_path.read_text(encoding="utf-8"))
    assert saved["status"] == result.status
    assert saved["stages"][0]["name"] == "sync"
