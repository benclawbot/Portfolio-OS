import json

from portfolio_os.generators import PortfolioDocumentGenerator


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_generates_changelog_release_notes_and_architecture(tmp_path):
    write_json(
        tmp_path / "portfolio" / "portfolio-summary.json",
        {
            "summary": {
                "active_count": 2,
                "analysis_coverage": 1.0,
                "intelligence_score": 82.5,
                "total_findings": 3,
            },
            "intelligence": {"averages": {"architecture": 80, "security": 85}},
            "repositories": [
                {
                    "full_name": "benclawbot/alpha",
                    "sync_status": "unchanged",
                    "head_sha": "abc",
                    "finding_count": 1,
                    "primary_language": "Python",
                    "frameworks": ["FastAPI"],
                    "file_count": 20,
                    "intelligence": {"scores": {"architecture": {"score": 81}}},
                }
            ],
        },
    )
    write_json(
        tmp_path / "history" / "latest-delta.json",
        {"summary": {"repositories_changed": 1, "regressions": 0}},
    )
    write_json(tmp_path / "portfolio" / "portfolio-graph.json", {"summary": {"node_count": 5, "edge_count": 4}})

    result = PortfolioDocumentGenerator(tmp_path).build()

    assert "repositories changed" in result.changelog_path.read_text().lower()
    assert "82.5/100" in result.release_notes_path.read_text()
    architecture = result.architecture_path.read_text()
    assert "FastAPI" in architecture
    assert "Nodes: **5**" in architecture


def test_generators_handle_missing_optional_delta_and_graph(tmp_path):
    write_json(tmp_path / "portfolio" / "portfolio-summary.json", {"summary": {}, "repositories": []})

    result = PortfolioDocumentGenerator(tmp_path).build()

    assert "No structured delta evidence" in result.changelog_path.read_text()
    assert "No previous snapshot delta" in result.release_notes_path.read_text()
