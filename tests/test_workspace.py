import json

from portfolio_os.workspace import WorkspaceValidator


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def seed_complete(tmp_path):
    write(tmp_path / "sync-state.json", "{}")
    write(tmp_path / "github" / "index.json", "{}")
    write(tmp_path / "portfolio" / "portfolio-summary.json", "{}")
    write(tmp_path / "portfolio" / "portfolio-report.md", "# report")
    write(tmp_path / "portfolio" / "portfolio-graph.json", "{}")
    write(tmp_path / "history" / "latest.json", "{}")
    write(tmp_path / "history" / "latest-delta.json", "{}")
    write(tmp_path / "trends" / "portfolio-trends.json", "{}")
    write(tmp_path / "dashboard" / "index.html", "<html></html>")
    write(tmp_path / "dashboard" / "dashboard-data.json", "{}")


def test_complete_workspace_passes_and_writes_manifest(tmp_path):
    seed_complete(tmp_path)
    result = WorkspaceValidator(tmp_path).validate()
    assert result.status == "passed"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["artifacts"]["sync_state"]["sha256"]
    assert manifest["artifacts"]["github_index"]["sha256"]


def test_missing_required_artifact_fails(tmp_path):
    seed_complete(tmp_path)
    (tmp_path / "trends" / "portfolio-trends.json").unlink()
    result = WorkspaceValidator(tmp_path).validate()
    assert result.status == "failed"
    assert any(check.name == "trends" and check.status == "failed" for check in result.checks)


def test_invalid_json_fails(tmp_path):
    seed_complete(tmp_path)
    write(tmp_path / "portfolio" / "portfolio-summary.json", "bad")
    result = WorkspaceValidator(tmp_path).validate()
    assert result.status == "failed"


def test_repair_plan_maps_missing_artifacts_to_stages(tmp_path):
    seed_complete(tmp_path)
    (tmp_path / "portfolio" / "portfolio-summary.json").unlink()
    (tmp_path / "dashboard" / "index.html").unlink()
    plan = WorkspaceValidator(tmp_path).repair_plan()
    assert plan["stages"] == ["report", "dashboard"]


def test_repair_plan_maps_missing_optional_index_to_index_stage(tmp_path):
    seed_complete(tmp_path)
    (tmp_path / "github" / "index.json").unlink()
    plan = WorkspaceValidator(tmp_path).repair_plan()
    assert plan["status"] == "passed"
    assert plan["stages"] == ["github-index"]
