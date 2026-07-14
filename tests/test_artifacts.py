import json

import pytest

from portfolio_os.artifacts import ArtifactManager


def write(path, content="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_catalogs_generated_artifacts_and_resolves_by_id(tmp_path):
    write(tmp_path / "portfolio" / "portfolio-summary.json")
    write(tmp_path / "backlog" / "portfolio-backlog.md", "# Backlog")
    manager = ArtifactManager(tmp_path)

    result = manager.build_catalog()

    payload = json.loads(result.catalog_path.read_text())
    assert result.artifact_count == 2
    assert payload["summary"]["categories"] == {"backlog": 1, "portfolio": 1}
    artifact_id = payload["artifacts"][0]["id"]
    assert manager.resolve(artifact_id).is_file()


def test_retention_is_plan_only_until_explicitly_confirmed(tmp_path):
    for index in range(4):
        write(tmp_path / "history" / "snapshots" / f"{index}.json")
    manager = ArtifactManager(tmp_path)
    plan = manager.retention_plan(keep_history=2, keep_runs=0)

    assert plan["delete_count"] == 2
    with pytest.raises(ValueError, match="confirm=True"):
        manager.apply_retention(plan)
    assert len(list((tmp_path / "history" / "snapshots").glob("*.json"))) == 4

    result = manager.apply_retention(plan, confirm=True)
    assert result["deleted_count"] == 2
    assert len(list((tmp_path / "history" / "snapshots").glob("*.json"))) == 2
