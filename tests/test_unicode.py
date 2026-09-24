"""Unicode round-trips through every interface (fake backend, no models)."""

import io
import json
import threading
from pathlib import Path

import pytest

from conftest import png_bytes, request
from textj.backends.base import BackendResult, OCRBackend
from textj.models import OCRLine

SAMPLES = (
    "안녕하세요 TextJ",
    "Hello, world!",
    "설정에서 CUDA provider를 활성화하세요",
    "총 1,234개 (80.0%) — p95 = 168.9 ms",
    "특수기호: ~!@#$%^&*()_+-=[]{};':\",./<>?₩€…「」",
    "파일을 C:\\Users\\홍길동\\model.onnx 에 저장했습니다",
    "https://example.com/문서?q=한글&lang=ko#섹션",
)


class UnicodeBackend(OCRBackend):
    name = "unicode-fake"

    def recognize(self, image) -> BackendResult:
        return BackendResult(lines=tuple(
            OCRLine(text, 0.9, ((0.0, i * 10.0), (5.0, i * 10.0), (5.0, i * 10.0 + 8), (0.0, i * 10.0 + 8)))
            for i, text in enumerate(SAMPLES)
        ))


EXPECTED = "\n".join(SAMPLES)


@pytest.fixture
def runtime(make_runtime):
    return make_runtime(UnicodeBackend())


@pytest.fixture
def hangul_image(tmp_path) -> Path:
    folder = tmp_path / "스크린샷 폴더"
    folder.mkdir()
    path = folder / "화면 캡처 (1).png"
    path.write_bytes(png_bytes())
    return path


def test_python_api_and_hangul_input_path(runtime, hangul_image) -> None:
    response = runtime.ocr(hangul_image)
    assert response["ok"], response
    assert response["result"]["text"] == EXPECTED
    assert [line["text"] for line in response["result"]["lines"]] == list(SAMPLES)


def test_handle_json_round_trip(runtime, hangul_image) -> None:
    raw = json.dumps(request(input={"type": "path", "path": str(hangul_image)}), ensure_ascii=True)
    assert json.loads(runtime.handle_json(raw))["result"]["text"] == EXPECTED
    raw = json.dumps(request(input={"type": "path", "path": str(hangul_image)}), ensure_ascii=False)
    assert json.loads(runtime.handle_json(raw.encode("utf-8")))["result"]["text"] == EXPECTED


def test_stdio_emits_utf8(runtime, hangul_image) -> None:
    from textj.transport.stdio import serve_stdio

    line = json.dumps(request(input={"type": "path", "path": str(hangul_image)}), ensure_ascii=False)
    stdout = io.BytesIO()
    serve_stdio(runtime, io.BytesIO(line.encode("utf-8") + b"\n"), stdout)
    raw = stdout.getvalue()
    assert "안녕하세요".encode("utf-8") in raw  # real UTF-8, not \\u escapes
    assert json.loads(raw.decode("utf-8"))["result"]["text"] == EXPECTED


def test_tcp_round_trip(runtime, hangul_image) -> None:
    from textj.transport.client import TextJClient
    from textj.transport.server import TextJServer

    server = TextJServer(runtime, host="127.0.0.1", port=0, token="t")
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    thread.start()
    try:
        with TextJClient("127.0.0.1", server.port, token="t") as client:
            assert client.ocr_path(hangul_image)["result"]["text"] == EXPECTED
            assert client.ocr_bytes(png_bytes(), request_id="요청-1")["request_id"] == "요청-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_mcp_structured_and_text_content(runtime, hangul_image) -> None:
    from textj.adapters.mcp_server import MCPServer

    server = MCPServer(runtime.handle)
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "ocr_image", "arguments": {"path": str(hangul_image)}}}
    stdout = io.BytesIO()
    server.serve(io.BytesIO(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"), stdout)
    result = json.loads(stdout.getvalue().decode("utf-8"))["result"]
    assert result["structuredContent"]["result"]["text"] == EXPECTED
    assert json.loads(result["content"][0]["text"])["result"]["text"] == EXPECTED
    assert result["structuredContent"]["result"]["lines"][0]["box"] is not None
    assert result["structuredContent"]["result"]["lines"][0]["score"] == 0.9


def test_ensure_utf8_stdio_reconfigures_legacy_pipes(monkeypatch) -> None:
    import sys

    from textj.app.common import ensure_utf8_stdio

    fake_out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    fake_err = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
    monkeypatch.setattr(sys, "stdout", fake_out)
    monkeypatch.setattr(sys, "stderr", fake_err)
    ensure_utf8_stdio()
    print("한글 ₩ OK")
    sys.stdout.flush()
    assert fake_out.buffer.getvalue().decode("utf-8").splitlines() == ["한글 ₩ OK"]
