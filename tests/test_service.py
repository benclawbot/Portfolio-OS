import json

import pytest

from portfolio_os.service import PortfolioService


def test_service_health_and_artifact_access(tmp_path):
    summary = tmp_path / "portfolio" / "portfolio-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"summary": {"repository_count": 1}}), encoding="utf-8")
    service = PortfolioService(tmp_path)

    assert service.health()["summary_available"] is True
    artifact = service.artifact("portfolio/portfolio-summary.json")
    assert artifact["content"]["summary"]["repository_count"] == 1


def test_service_rejects_workspace_escape(tmp_path):
    service = PortfolioService(tmp_path)
    with pytest.raises(ValueError, match="escapes workspace"):
        service.artifact("../secret.txt")


def test_service_submits_and_runs_backlog_job(tmp_path):
    summary = tmp_path / "portfolio" / "portfolio-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"repositories": []}), encoding="utf-8")
    service = PortfolioService(tmp_path)

    submitted = service.submit("backlog")
    completed = service.run_next()

    assert submitted["status"] == "pending"
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["result"]["item_count"] == 0


def test_service_rejects_unsupported_job(tmp_path):
    service = PortfolioService(tmp_path)
    with pytest.raises(ValueError, match="unsupported job kind"):
        service.submit("unknown")
