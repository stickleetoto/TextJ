import json
import threading
import time

import numpy as np
import pytest

from conftest import ControllableBackend, b64, png_bytes, request
from textj.api import ErrorCode, TextJError
from textj.runtime import RuntimeConfig, RuntimeState, TextJRuntime


def path_request(path, **fields):
    return request(input={"type": "path", "path": str(path)}, **fields)


def test_backend_constructed_once_and_warmed(png_path) -> None:
    constructed = []

    def factory():
        backend = ControllableBackend()
        constructed.append(backend)
        return backend

    with TextJRuntime(RuntimeConfig(), backend_factory=factory) as runtime:
        for _ in range(5):
            assert runtime.handle(path_request(png_path))["ok"]
        status = runtime.status()

    assert len(constructed) == 1
    assert constructed[0].calls == 6  # warmup + 5 requests
    assert constructed[0].closed
    assert status["counters"]["ok"] == 5
    assert "warmup_ms" in status["startup_ms"]
    assert runtime.state is RuntimeState.CLOSED


def test_success_response_schema(make_runtime, png_path) -> None:
    runtime = make_runtime()
    response = runtime.handle(path_request(png_path, request_id="abc"))

    assert list(response) == ["protocol_version", "request_id", "ok", "result"]
    assert response["protocol_version"] == "1"
    assert response["request_id"] == "abc"
    result = response["result"]
    assert list(result) == [
        "text", "lines", "line_count", "mean_score", "backend", "input", "timings_ms",
    ]
    # default min_score 0.5 filters the 0.2 line
    assert result["text"] == "안녕하세요 TextJ"
    assert result["lines"] == [{
        "text": "안녕하세요 TextJ",
        "score": 0.97,
        "box": [[1.0, 2.0], [30.0, 2.0], [30.0, 9.0], [1.0, 9.0]],
    }]
    assert result["input"]["width"] == 40 and result["input"]["height"] == 20
    timings = result["timings_ms"]
    for key in ("parse", "queue", "input", "ocr", "detect", "recognize", "postprocess", "total"):
        assert key in timings
    assert timings["total"] >= timings["ocr"]
    json.dumps(response, allow_nan=False)


def test_options_min_score_boxes_timings(make_runtime, png_path) -> None:
    runtime = make_runtime()
    result = runtime.handle(path_request(
        png_path,
        options={"min_score": 0.0, "include_boxes": False, "include_timings": False},
    ))["result"]
    assert result["line_count"] == 2
    assert "box" not in result["lines"][0]
    assert "timings_ms" not in result


def test_language_mismatch_is_invalid_request(make_runtime, png_path) -> None:
    runtime = make_runtime(language="korean")
    response = runtime.handle(path_request(png_path, options={"language": "en"}))
    assert response["error"]["code"] == "INVALID_REQUEST"
    assert response["error"]["details"]["supported"] == ["korean"]
    assert runtime.handle(path_request(png_path, options={"language": "korean"}))["ok"]


def test_python_api_accepts_ndarray_bytes_and_path(make_runtime, png_path) -> None:
    backend = ControllableBackend()
    runtime = make_runtime(backend)
    assert runtime.ocr(np.zeros((8, 16), dtype=np.uint8))["ok"]
    assert runtime.ocr(png_bytes())["ok"]
    assert runtime.ocr(str(png_path))["ok"]
    assert runtime.ocr(png_path, request_id="p")["request_id"] == "p"
    assert backend.shapes[1:] == [(8, 16, 3), (20, 40, 3), (20, 40, 3), (20, 40, 3)]
    bad = runtime.ocr(png_path, min_score=5)
    assert bad["error"]["code"] == "INVALID_REQUEST"


def test_error_paths_are_structured(make_runtime, tmp_path) -> None:
    runtime = make_runtime(ControllableBackend(fail=True), warmup=False)
    assert runtime.handle(path_request(tmp_path / "nope.png"))["error"]["code"] == "IMAGE_NOT_FOUND"
    response = runtime.handle(request(input={"type": "bytes_base64", "data": b64(b"xx")}))
    assert response["error"]["code"] == "IMAGE_DECODE_FAILED"
    response = runtime.handle(request(input={"type": "bytes_base64", "data": b64(png_bytes())}))
    assert response["error"]["code"] == "OCR_FAILED"
    assert response["error"]["retryable"] is False
    status = runtime.status()
    assert status["errors_by_code"] == {
        "IMAGE_DECODE_FAILED": 1, "IMAGE_NOT_FOUND": 1, "OCR_FAILED": 1,
    }
    # runtime keeps serving after backend exceptions
    assert status["state"] == "ready"


def test_handle_json_errors(make_runtime) -> None:
    runtime = make_runtime(limits=__import__("textj").api.Limits(max_request_bytes=200))
    assert json.loads(runtime.handle_json("{nope"))["error"]["code"] == "INVALID_REQUEST"
    assert json.loads(runtime.handle_json("x" * 500))["error"]["code"] == "REQUEST_TOO_LARGE"
    status = json.loads(runtime.handle_json('{"protocol_version":"1","operation":"status","request_id":"s"}'))
    assert status["ok"] and status["request_id"] == "s"
    assert status["result"]["ready"] is True


def test_status_before_start_and_not_ready() -> None:
    runtime = TextJRuntime(RuntimeConfig(), backend_factory=ControllableBackend)
    status = runtime.handle(request("status"))
    assert status["result"]["state"] == "created"
    response = runtime.handle(request(input={"type": "bytes_base64", "data": b64(png_bytes())}))
    assert response["error"]["code"] == "BACKEND_NOT_READY"
    assert response["error"]["retryable"] is True


def test_backend_startup_failure_sets_failed_state() -> None:
    def broken():
        raise OSError("model download failed")

    runtime = TextJRuntime(RuntimeConfig(), backend_factory=broken)
    with pytest.raises(TextJError) as info:
        runtime.start()
    assert info.value.code is ErrorCode.BACKEND_NOT_READY
    assert runtime.state is RuntimeState.FAILED
    response = runtime.handle(request(input={"type": "bytes_base64", "data": b64(png_bytes())}))
    assert response["error"]["code"] == "BACKEND_NOT_READY"
    assert response["error"]["retryable"] is False
    assert "model download failed" in runtime.status()["failure"]
    runtime.close()
    assert runtime.state is RuntimeState.CLOSED


def wait_for_scheduler(runtime, inflight, queued, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        scheduler = runtime.status()["scheduler"]
        if scheduler["inflight"] == inflight and scheduler["queued"] == queued:
            return
        time.sleep(0.002)
    raise AssertionError(f"scheduler did not reach inflight={inflight} queued={queued}")


def run_in_threads(fn, count):
    results = [None] * count

    def target(index):
        results[index] = fn(index)

    threads = [threading.Thread(target=target, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    return threads, results


def test_busy_when_queue_full(make_runtime) -> None:
    gate = threading.Event()
    backend = ControllableBackend(gate=gate)
    runtime = make_runtime(backend, max_inflight=1, max_queue=1, warmup=False)
    data = png_bytes()

    threads, results = run_in_threads(lambda i: runtime.ocr(data, request_id=f"r{i}"), 2)
    wait_for_scheduler(runtime, inflight=1, queued=1)
    assert runtime.status()["scheduler"] == {
        "max_inflight": 1, "max_queue": 1, "inflight": 1, "queued": 1,
    }

    rejected = runtime.ocr(data, request_id="overflow")
    assert rejected["error"]["code"] == "BUSY"
    assert rejected["error"]["retryable"] is True

    gate.set()
    for thread in threads:
        thread.join(5)
    assert all(result["ok"] for result in results)
    assert runtime.status()["counters"]["busy_rejects"] == 1


def test_max_queue_zero_means_no_waiting(make_runtime) -> None:
    gate = threading.Event()
    runtime = make_runtime(ControllableBackend(gate=gate), max_queue=0, warmup=False)
    data = png_bytes()
    threads, results = run_in_threads(lambda i: runtime.ocr(data), 1)
    wait_for_scheduler(runtime, inflight=1, queued=0)
    assert runtime.ocr(data)["error"]["code"] == "BUSY"
    gate.set()
    threads[0].join(5)
    assert results[0]["ok"]


def test_timeout_while_queued_frees_the_slot(make_runtime) -> None:
    gate = threading.Event()
    backend = ControllableBackend(gate=gate)
    runtime = make_runtime(backend, max_inflight=1, max_queue=1, warmup=False)
    data = png_bytes()

    threads, results = run_in_threads(lambda i: runtime.ocr(data), 1)
    wait_for_scheduler(runtime, inflight=1, queued=0)

    timed_out = runtime.ocr(data, timeout_ms=50)
    assert timed_out["error"]["code"] == "TIMEOUT"
    assert timed_out["error"]["retryable"] is True
    # the queued job was removed, so the queue slot is free again
    assert runtime.status()["scheduler"]["queued"] == 0

    gate.set()
    threads[0].join(5)
    assert results[0]["ok"]
    assert backend.calls == 1  # the timed-out request never reached the backend
    assert runtime.status()["counters"]["timeouts"] == 1


def test_timeout_while_running_is_bounded(make_runtime) -> None:
    backend = ControllableBackend(delay=0.3)
    runtime = make_runtime(backend, warmup=False)
    started = time.perf_counter()
    response = runtime.ocr(png_bytes(), timeout_ms=50)
    elapsed = time.perf_counter() - started
    assert response["error"]["code"] == "TIMEOUT"
    assert elapsed < 0.25
    # the running inference still occupies its slot until it ends
    time.sleep(0.4)
    assert runtime.status()["scheduler"]["inflight"] == 0
    assert runtime.ocr(png_bytes())["ok"]


def test_concurrent_requests_all_complete(make_runtime) -> None:
    runtime = make_runtime(ControllableBackend(delay=0.005), max_inflight=1, max_queue=32, warmup=False)
    data = png_bytes()
    threads, results = run_in_threads(lambda i: runtime.ocr(data, request_id=f"r{i}"), 16)
    for thread in threads:
        thread.join(10)
    assert [r["request_id"] for r in results] == [f"r{i}" for i in range(16)]
    assert all(r["ok"] for r in results)
    queue_times = [r["result"]["timings_ms"]["queue"] for r in results]
    assert max(queue_times) > 0


def test_multiple_workers_own_separate_backends(png_path) -> None:
    made = []

    def factory():
        backend = ControllableBackend(delay=0.05)
        made.append(backend)
        return backend

    with TextJRuntime(RuntimeConfig(max_inflight=2, warmup=False), backend_factory=factory) as runtime:
        threads, results = run_in_threads(lambda i: runtime.ocr(png_path), 4)
        for thread in threads:
            thread.join(5)
    assert len(made) == 2
    assert all(r["ok"] for r in results)
    assert sum(b.calls for b in made) == 4


def test_batch_preserves_order_and_item_errors(make_runtime, png_path, tmp_path) -> None:
    runtime = make_runtime()
    response = runtime.handle(request(
        "ocr_batch",
        request_id="b",
        items=[
            {"id": "a", "input": {"type": "path", "path": str(png_path)}},
            {"id": "missing", "input": {"type": "path", "path": str(tmp_path / "x.png")}},
            {"id": "badb64", "input": {"type": "bytes_base64", "data": "@@"}},
            {"id": "c", "input": {"type": "bytes_base64", "data": b64(png_bytes())}},
        ],
    ))
    assert response["ok"] and response["request_id"] == "b"
    result = response["result"]
    assert [item["id"] for item in result["items"]] == ["a", "missing", "badb64", "c"]
    assert [item["ok"] for item in result["items"]] == [True, False, False, True]
    assert result["items"][1]["error"]["code"] == "IMAGE_NOT_FOUND"
    assert result["items"][2]["error"]["code"] == "INVALID_REQUEST"
    assert result["items"][0]["result"]["text"] == "안녕하세요 TextJ"
    assert (result["item_count"], result["succeeded"], result["failed"]) == (4, 2, 2)
    assert "total" in result["timings_ms"]


def test_batch_deadline_returns_partial_results(make_runtime) -> None:
    runtime = make_runtime(ControllableBackend(delay=0.08), warmup=False, batch_grace_ms=1000)
    data = b64(png_bytes())
    response = runtime.handle(request(
        "ocr_batch",
        timeout_ms=120,
        items=[{"id": str(i), "input": {"type": "bytes_base64", "data": data}} for i in range(5)],
    ))
    assert response["ok"]
    items = response["result"]["items"]
    assert items[0]["ok"] is True
    assert items[-1]["error"]["code"] == "TIMEOUT"
    assert response["result"]["succeeded"] < 5


def test_close_fails_queued_jobs_and_rejects_new(png_path) -> None:
    gate = threading.Event()
    runtime = TextJRuntime(
        RuntimeConfig(max_queue=4, warmup=False),
        backend_factory=lambda: ControllableBackend(gate=gate),
    ).start()
    threads, results = run_in_threads(lambda i: runtime.ocr(png_path), 3)
    wait_for_scheduler(runtime, inflight=1, queued=2)

    closer = threading.Thread(target=runtime.close)
    closer.start()
    time.sleep(0.05)
    gate.set()
    closer.join(5)
    for thread in threads:
        thread.join(5)

    codes = sorted("ok" if r["ok"] else r["error"]["code"] for r in results)
    assert codes == ["BACKEND_NOT_READY", "BACKEND_NOT_READY", "ok"]
    assert runtime.ocr(png_path)["error"]["code"] == "BACKEND_NOT_READY"
    assert runtime.state is RuntimeState.CLOSED
