import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from portfolio_os.service import PortfolioHTTPServer, PortfolioService


@contextmanager
def running_server(tmp_path):
    server = PortfolioHTTPServer(("127.0.0.1", 0), PortfolioService(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(url, *, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status, json.load(response)


def test_service_health_and_artifact_access(tmp_path):
    summary = tmp_path / "portfolio" / "portfolio-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"summary": {"repository_count": 1}}), encoding="utf-8")
    service = PortfolioService(tmp_path)

    assert service.health()["summary_available"] is True
    artifact = service.artifact("portfolio/portfolio-summary.json")
    assert artifact["content"]["summary"]["repository_count"] == 1
    catalog = service.catalog()
    artifact_id = catalog["artifacts"][0]["id"]
    assert service.artifact_by_id(artifact_id)["path"] == "portfolio/portfolio-summary.json"


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


def test_http_health_job_and_artifact_routes(tmp_path):
    summary = tmp_path / "portfolio" / "portfolio-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"repositories": []}), encoding="utf-8")

    with running_server(tmp_path) as base:
        status, health = request_json(f"{base}/v1/health")
        assert status == 200
        assert health["status"] == "ok"

        status, submitted = request_json(
            f"{base}/v1/jobs",
            method="POST",
            payload={"kind": "backlog", "parameters": {}},
        )
        assert status == 202
        job_id = submitted["id"]

        status, ran = request_json(f"{base}/v1/jobs/run-next", method="POST", payload={})
        assert status == 200
        assert ran["job"]["status"] == "completed"

        status, fetched = request_json(f"{base}/v1/jobs/{job_id}")
        assert fetched["status"] == "completed"

        status, catalog = request_json(f"{base}/v1/artifacts/catalog")
        assert status == 200
        artifact_id = catalog["artifacts"][0]["id"]
        status, artifact = request_json(f"{base}/v1/artifacts/{artifact_id}")
        assert artifact["content"]["repositories"] == []


def test_http_reports_bad_routes_and_payloads(tmp_path):
    with running_server(tmp_path) as base:
        with pytest.raises(urllib.error.HTTPError) as missing:
            request_json(f"{base}/v1/missing")
        assert missing.value.code == 404

        with pytest.raises(urllib.error.HTTPError) as invalid:
            request_json(f"{base}/v1/jobs", method="POST", payload={"kind": "unknown"})
        assert invalid.value.code == 400
