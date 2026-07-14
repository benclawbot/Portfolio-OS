from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from portfolio_os.artifacts import ArtifactManager
from portfolio_os.backlog import PortfolioBacklog
from portfolio_os.generators import PortfolioDocumentGenerator
from portfolio_os.jobs import JobQueue
from portfolio_os.portfolio import PortfolioBuilder
from portfolio_os.trends import PortfolioTrends


class PortfolioService:
    """Local service facade used by the HTTP API and future Medusa integration."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.jobs = JobQueue(self.workspace)
        self.artifacts = ArtifactManager(self.workspace)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "workspace": str(self.workspace),
            "summary_available": (self.workspace / "portfolio" / "portfolio-summary.json").exists(),
        }

    def artifact(self, relative: str) -> dict[str, Any]:
        path = (self.workspace / relative).resolve()
        if self.workspace not in path.parents and path != self.workspace:
            raise ValueError("artifact path escapes workspace")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(relative)
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {"path": relative, "content_type": "application/json", "content": payload}
        return {"path": relative, "content_type": "text/plain", "content": path.read_text(encoding="utf-8")}

    def artifact_by_id(self, artifact_id: str) -> dict[str, Any]:
        path = self.artifacts.resolve(artifact_id)
        return self.artifact(path.relative_to(self.workspace).as_posix())

    def catalog(self) -> dict[str, Any]:
        result = self.artifacts.build_catalog()
        return json.loads(result.catalog_path.read_text(encoding="utf-8"))

    def submit(self, kind: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        allowed = {"report", "backlog", "trends", "documents", "artifacts"}
        if kind not in allowed:
            raise ValueError(f"unsupported job kind: {kind}")
        return self.jobs.submit(kind, parameters).to_dict()

    def run_next(self) -> dict[str, Any] | None:
        def run_report(parameters: dict[str, Any]) -> dict[str, Any]:
            result = PortfolioBuilder(self.workspace).build(float(parameters.get("similarity_threshold", 0.55)))
            return {
                "summary_path": str(result.summary_path),
                "report_path": str(result.report_path),
                "graph_path": str(result.graph_path),
            }

        def run_trends(parameters: dict[str, Any]) -> dict[str, Any]:
            limit = parameters.get("limit")
            result = PortfolioTrends(self.workspace).build(int(limit) if limit is not None else None)
            return {
                "json_path": str(result.json_path),
                "report_path": str(result.report_path),
                "snapshot_count": result.data.get("snapshot_count", 0),
            }

        handlers = {
            "report": run_report,
            "backlog": lambda parameters: PortfolioBacklog(self.workspace).build().to_dict(),
            "trends": run_trends,
            "documents": lambda parameters: PortfolioDocumentGenerator(self.workspace).build().to_dict(),
            "artifacts": lambda parameters: ArtifactManager(self.workspace).build_catalog().to_dict(),
        }
        result = self.jobs.run_next(handlers)
        return result.to_dict() if result else None


class PortfolioRequestHandler(BaseHTTPRequestHandler):
    server_version = "PortfolioOS/1.0"

    @property
    def service(self) -> PortfolioService:
        server = cast(PortfolioHTTPServer, self.server)
        return server.service

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/v1/health":
                self._json(HTTPStatus.OK, self.service.health())
                return
            if parsed.path == "/v1/jobs":
                status = parse_qs(parsed.query).get("status", [None])[0]
                self._json(HTTPStatus.OK, {"jobs": [item.to_dict() for item in self.service.jobs.list(status)]})
                return
            if parsed.path.startswith("/v1/jobs/"):
                job_id = parsed.path.rsplit("/", 1)[-1]
                job = self.service.jobs.get(job_id)
                if job is None:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                else:
                    self._json(HTTPStatus.OK, job.to_dict())
                return
            if parsed.path == "/v1/artifacts/catalog":
                self._json(HTTPStatus.OK, self.service.catalog())
                return
            if parsed.path.startswith("/v1/artifacts/"):
                artifact_id = parsed.path.rsplit("/", 1)[-1]
                self._json(HTTPStatus.OK, self.service.artifact_by_id(artifact_id))
                return
            if parsed.path == "/v1/artifacts":
                relative = parse_qs(parsed.query).get("path", [""])[0]
                self._json(HTTPStatus.OK, self.service.artifact(relative))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
        except FileNotFoundError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "artifact not found"})
        except KeyError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "artifact id not found"})
        except (ValueError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_POST(self) -> None:
        try:
            payload = self._body()
            if self.path == "/v1/jobs":
                parameters = payload.get("parameters")
                if parameters is not None and not isinstance(parameters, dict):
                    raise ValueError("parameters must be an object")
                self._json(
                    HTTPStatus.ACCEPTED,
                    self.service.submit(str(payload.get("kind", "")), parameters or {}),
                )
                return
            if self.path == "/v1/jobs/run-next":
                result = self.service.run_next()
                self._json(HTTPStatus.OK, {"job": result})
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
        except (ValueError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PortfolioHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service: PortfolioService) -> None:
        super().__init__(address, PortfolioRequestHandler)
        self.service = service


def serve(workspace: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = PortfolioHTTPServer((host, port), PortfolioService(workspace))
    server.serve_forever()
