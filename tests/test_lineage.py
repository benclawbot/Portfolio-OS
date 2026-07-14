import json

from portfolio_os.lineage import RepositoryLineage
from portfolio_os.sync import RepositoryState, SyncState, save_state_atomic


def repository(repo_id, name):
    return RepositoryState(
        id=repo_id,
        name=name,
        full_name=f"benclawbot/{name}",
        path=f"/workspace/{name}",
        default_branch="main",
        head_sha="abc",
        visibility="private",
        fork=False,
        archived=False,
        updated_at="2026-07-14T00:00:00Z",
        status="unchanged",
    )


def test_builds_merge_archive_and_migration_lineage(tmp_path):
    save_state_atomic(
        SyncState(
            owner="benclawbot",
            repositories={
                "1": repository(1, "Medusa"),
                "2": repository(2, "FastBot"),
                "3": repository(3, "Zeus"),
            },
        ),
        tmp_path / "sync-state.json",
    )
    config = tmp_path / "portfolio.json"
    config.write_text(
        json.dumps(
            {
                "owner": "benclawbot",
                "repositories": [
                    {
                        "name": "FastBot",
                        "classification": "merge-into-medusa",
                        "next_action": "Extract useful concepts into Medusa, then archive.",
                    },
                    {
                        "name": "Zeus",
                        "classification": "migration-source",
                        "next_action": "Extract GUI into Medusa Desktop.",
                    },
                    {
                        "name": "Old",
                        "classification": "archive-candidate",
                        "next_action": "Archive after extraction.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = RepositoryLineage(tmp_path, config).build()

    payload = json.loads(result.json_path.read_text())
    edges = {(item["source"], item["relation"], item["target"]) for item in payload["edges"]}
    assert ("benclawbot/FastBot", "merge_into", "benclawbot/Medusa") in edges
    assert ("benclawbot/Zeus", "migration_source_for", "benclawbot/Medusa") in edges
    assert ("benclawbot/Old", "archive_candidate", None) in edges
    assert payload["impact"]["inbound"]["benclawbot/Medusa"]
