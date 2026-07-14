import json

from portfolio_os.operations import RefreshOperations
from portfolio_os.telemetry import TelemetryReporter


def test_telemetry_aggregates_run_and_stage_metrics(tmp_path):
    operations = RefreshOperations(tmp_path)
    operations.record_run(
        {
            "status": "completed",
            "duration_seconds": 2.0,
            "stages": [
                {"name": "sync", "status": "completed", "duration_seconds": 1.5},
                {"name": "report", "status": "completed", "duration_seconds": 0.5},
            ],
        }
    )
    operations.record_run(
        {
            "status": "failed",
            "duration_seconds": 1.0,
            "stages": [{"name": "sync", "status": "failed", "duration_seconds": 1.0}],
        }
    )

    result = TelemetryReporter(tmp_path).build()

    payload = json.loads(result.path.read_text())
    assert result.run_count == 2
    assert result.failure_count == 1
    assert payload["summary"]["success_rate"] == 0.5
    assert payload["stages"]["sync"]["run_count"] == 2
    assert payload["stages"]["sync"]["failure_count"] == 1
    assert payload["privacy"]["network_export"] is False


def test_empty_telemetry_is_valid(tmp_path):
    result = TelemetryReporter(tmp_path).build()
    payload = json.loads(result.path.read_text())
    assert result.run_count == 0
    assert payload["summary"]["success_rate"] == 0.0
