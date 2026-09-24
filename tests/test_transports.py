import io
import json
import os
import socket
import stat
import threading

import pytest

from conftest import ControllableBackend, b64, png_bytes, request
from textj.transport.client import TextJClient, TextJClientError
from textj.transport.framing import LineTooLong, read_line
from textj.transport.server import TextJServer, ensure_loopback, write_state_file
from textj.transport.stdio import serve_stdio


def lines_of(buffer: io.BytesIO) -> list[dict]:
    return [json.loads(line) for line in buffer.getvalue().decode("utf-8").splitlines()]


# ---------------------------------------------------------------- framing


def test_read_line_bounds_memory() -> None:
    stream = io.BytesIO(b"short\n" + b"x" * 100 + b"\nnext\nlast")
    assert read_line(stream, 10) == b"short"
    with pytest.raises(LineTooLong):
        read_line(stream, 10)
    assert read_line(stream, 10) == b"next"
    assert read_line(stream, 10) == b"last"
    assert read_line(stream, 10) is None


# ---------------------------------------------------------------- stdio


def test_stdio_round_trip(make_runtime, png_path) -> None:
    from textj.api import Limits

    runtime = make_runtime(limits=Limits(max_request_bytes=4096))
    messages = [
        json.dumps(request(request_id="1", input={"type": "path", "path": str(png_path)})),
        "",
        "{broken",
        json.dumps(request("status", request_id="2")),
        "y" * 5000,
        json.dumps(request(request_id="3", input={"type": "bytes_base64", "data": b64(png_bytes())})),
    ]
    stdin = io.BytesIO(("\n".join(messages) + "\n").encode("utf-8"))
    stdout = io.BytesIO()

    handled = serve_stdio(runtime, stdin, stdout)

    responses = lines_of(stdout)
    assert handled == 5 == len(responses)
    assert responses[0]["ok"] and responses[0]["request_id"] == "1"
    assert responses[0]["result"]["text"] == "안녕하세요 TextJ"
    assert responses[1]["error"]["code"] == "INVALID_REQUEST"
    assert responses[2]["result"]["state"] == "ready"
    assert responses[3]["error"]["code"] == "REQUEST_TOO_LARGE"
    assert responses[4]["ok"] and responses[4]["request_id"] == "3"


# ---------------------------------------------------------------- daemon


@pytest.fixture
def daemon(make_runtime):
    started = []

    def start(backend=None, token="secret", **kwargs):
        runtime = make_runtime(backend, **kwargs.pop("runtime", {}))
        server = TextJServer(runtime, host="127.0.0.1", port=0, token=token, **kwargs)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        started.append((server, thread))
        return server

    yield start
    for server, thread in started:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_loopback_only() -> None:
    ensure_loopback("127.0.0.1")
    ensure_loopback("::1")
    ensure_loopback("localhost")
    for host in ("0.0.0.0", "192.168.1.10", "example.com"):
        with pytest.raises(ValueError):
            ensure_loopback(host)


def test_client_round_trip(daemon, png_path) -> None:
    server = daemon()
    with TextJClient("127.0.0.1", server.port, token="secret") as client:
        status = client.status(request_id="s")
        assert status["ok"] and status["request_id"] == "s"
        first = client.ocr_path(png_path, request_id="a")
        second = client.ocr_bytes(png_bytes(), min_score=0.0, include_boxes=False)
        batch = client.ocr_batch([
            {"id": "x", "input": {"type": "path", "path": str(png_path)}},
            {"id": "y", "input": {"type": "path", "path": "/definitely/missing.png"}},
        ])
    assert first["ok"] and first["request_id"] == "a"
    assert first["result"]["input"]["source"] == "path"
    assert second["result"]["line_count"] == 2 and "box" not in second["result"]["lines"][0]
    assert [item["ok"] for item in batch["result"]["items"]] == [True, False]


def test_auth_token_required(daemon, png_path) -> None:
    server = daemon()
    with TextJClient("127.0.0.1", server.port, token="wrong") as client:
        response = client.status(request_id="r")
    assert response["error"]["code"] == "UNAUTHORIZED"
    assert response["request_id"] == "r"
    with TextJClient("127.0.0.1", server.port) as client:
        assert client.status()["error"]["code"] == "UNAUTHORIZED"


def test_no_auth_mode(daemon) -> None:
    server = daemon(token=None)
    with TextJClient("127.0.0.1", server.port) as client:
        assert client.status()["ok"]


def test_malformed_lines_keep_connection_open(daemon) -> None:
    server = daemon(token=None)
    with socket.create_connection(("127.0.0.1", server.port), timeout=5) as sock:
        stream = sock.makefile("rwb")
        stream.write(b"not json\n[]\n" + json.dumps(request("status")).encode() + b"\n")
        stream.flush()
        responses = [json.loads(stream.readline()) for _ in range(3)]
    assert responses[0]["error"]["code"] == "INVALID_REQUEST"
    assert responses[1]["error"]["code"] == "INVALID_REQUEST"
    assert responses[2]["ok"]


def test_connection_limit(daemon) -> None:
    server = daemon(token=None, max_connections=1)
    with TextJClient("127.0.0.1", server.port) as first:
        assert first.status()["ok"]
        with socket.create_connection(("127.0.0.1", server.port), timeout=5) as sock:
            response = json.loads(sock.makefile("rb").readline())
    assert response["error"]["code"] == "BUSY"


def test_parallel_clients_get_busy_not_unbounded_queue(daemon) -> None:
    gate = threading.Event()
    server = daemon(
        ControllableBackend(gate=gate), token=None,
        runtime={"max_queue": 1, "warmup": False},
    )
    results = []

    def call():
        with TextJClient("127.0.0.1", server.port) as client:
            results.append(client.ocr_bytes(png_bytes()))

    threads = [threading.Thread(target=call) for _ in range(5)]
    for thread in threads:
        thread.start()
    # 1 running + 1 queued are admitted; the rest are rejected immediately.
    import time
    deadline = time.monotonic() + 3
    while len(results) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    gate.set()
    for thread in threads:
        thread.join(5)
    codes = sorted("ok" if r["ok"] else r["error"]["code"] for r in results)
    assert codes == ["BUSY", "BUSY", "BUSY", "ok", "ok"]


def test_client_errors_when_daemon_absent() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(TextJClientError):
        TextJClient("127.0.0.1", port, timeout=1).status()


def test_state_file_permissions_and_discovery(tmp_path, daemon) -> None:
    server = daemon()
    state = tmp_path / "state" / "daemon.json"
    write_state_file(state, server.state_payload())
    if os.name == "posix":
        assert stat.S_IMODE(state.stat().st_mode) == 0o600
    with TextJClient.from_state_file(state) as client:
        assert client.status()["ok"]
    with pytest.raises(TextJClientError):
        TextJClient.from_state_file(tmp_path / "missing.json")
