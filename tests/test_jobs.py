from portfolio_os.jobs import JobQueue


def test_job_queue_completes_and_persists_result(tmp_path):
    queue = JobQueue(tmp_path)
    job = queue.submit("echo", {"value": 3})

    result = queue.run_next({"echo": lambda parameters: {"value": parameters["value"]}})

    assert result is not None
    assert result.id == job.id
    assert result.status == "completed"
    assert result.result == {"value": 3}
    assert queue.get(job.id) == result
    assert queue.list("completed") == [result]


def test_job_queue_records_handler_failure(tmp_path):
    queue = JobQueue(tmp_path)
    job = queue.submit("broken")

    result = queue.run_next({"broken": lambda parameters: (_ for _ in ()).throw(RuntimeError("boom"))})

    assert result is not None
    assert result.id == job.id
    assert result.status == "failed"
    assert result.error == "RuntimeError: boom"
    assert queue.list("pending") == []


def test_job_queue_returns_none_when_empty(tmp_path):
    assert JobQueue(tmp_path).run_next({}) is None
