from pathlib import Path

from portfolio_os.engine import AnalysisEngine


def test_analysis_detects_repository_facts() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    data = analysis.to_dict()
    assert data["repository"] == "sample_repo"
    assert data["facts"]["languages"]["primary"] == "Python"
    assert data["facts"]["quality"]["test_file_count"] == 1
    assert data["facts"]["quality"]["workflows"] == [".github/workflows/ci.yml"]
    assert "fastapi>=0.100" in data["facts"]["manifests"]["dependencies"]["python"]
    assert data["summary"]["error_count"] == 0


def test_analysis_reports_missing_governance_files() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    codes = {finding.code for finding in analysis.findings}
    assert "missing-license" in codes
    assert "missing-security.md" in codes
    assert "readme-too-short" in codes


def test_analysis_json_round_trip(tmp_path: Path) -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    output = tmp_path / "analysis.json"
    analysis.write_json(output)
    assert '"repository": "sample_repo"' in output.read_text(encoding="utf-8")
