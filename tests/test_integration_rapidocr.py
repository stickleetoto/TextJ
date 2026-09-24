"""Real OCR integration tests (opt-in): ``pytest -m integration``.

English runs on the PP-OCRv6 small models bundled in the rapidocr wheel (no
download). Korean / mixed tests run when the PP-OCRv5 ko-en model files are
available locally (``textj-models fetch``), or with ``TEXTJ_KOREAN_MODELS=1``
which allows downloading them at runtime start.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from textj.accuracy import character_error_rate

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"
# Loose bound: catches broken pipelines/language setups, not small accuracy
# shifts (use textj-bench-compare for those).
MAX_CER = 0.15


def load_cases(tags):
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    return [case for case in manifest["cases"] if set(case["tags"]) & set(tags)]


def expected(case) -> str:
    return (FIXTURES / case["expected"]).read_text(encoding="utf-8")


def korean_models_available() -> bool:
    if os.environ.get("TEXTJ_KOREAN_MODELS") == "1":
        return True
    try:
        from textj import model_store

        return all(model_store.find_model(s) for s in model_store.specs_for("ppocrv5-mobile", "ko-en"))
    except Exception:
        return False


needs_korean = pytest.mark.skipif(
    not korean_models_available(),
    reason="PP-OCRv5 ko-en models not cached (run: textj-models fetch) "
           "and TEXTJ_KOREAN_MODELS=1 not set",
)

ENGLISH_TAGS = {"EN", "CODE", "TERM", "DARK", "TINY"}
KOREAN_TAGS = {"KO", "MIX"}


@pytest.fixture(scope="module")
def english_runtime():
    pytest.importorskip("rapidocr")
    from textj.runtime import RuntimeConfig, TextJRuntime

    runtime = TextJRuntime(RuntimeConfig(language="en", profile="ppocrv6-small")).start()
    yield runtime
    runtime.close()


@pytest.fixture(scope="module")
def ko_en_runtime():
    if not korean_models_available():
        pytest.skip("Korean models unavailable")
    from textj.runtime import RuntimeConfig, TextJRuntime

    runtime = TextJRuntime(RuntimeConfig(language="ko-en", profile="ppocrv5-mobile")).start()
    yield runtime
    runtime.close()


def english_cases():
    return [c for c in load_cases(ENGLISH_TAGS) if not set(c["tags"]) & KOREAN_TAGS]


@pytest.mark.parametrize("case", english_cases(), ids=lambda c: c["id"])
def test_english_fixture_cer(english_runtime, case) -> None:
    response = english_runtime.handle({
        "protocol_version": "1",
        "operation": "ocr",
        "input": {"type": "path", "path": str(FIXTURES / case["image"])},
    })
    assert response["ok"], response
    assert character_error_rate(expected(case), response["result"]["text"]) < MAX_CER


@needs_korean
@pytest.mark.parametrize("case", load_cases(KOREAN_TAGS | ENGLISH_TAGS), ids=lambda c: c["id"])
def test_ko_en_runtime_fixture_cer(ko_en_runtime, case) -> None:
    """One ko-en runtime must handle English, Korean and mixed fixtures."""
    response = ko_en_runtime.ocr(FIXTURES / case["image"])
    assert response["ok"], response
    cer = character_error_rate(expected(case), response["result"]["text"])
    assert cer < MAX_CER, (case["id"], cer, response["result"]["text"])


@needs_korean
def test_mixed_language_batch(ko_en_runtime) -> None:
    items = [
        {"id": "en", "input": {"type": "path", "path": str(FIXTURES / "images/en-ui-001.png")}},
        {"id": "ko", "input": {"type": "path", "path": str(FIXTURES / "images/ko-ui-001.png")}},
        {"id": "mix", "input": {"type": "path", "path": str(FIXTURES / "images/mix-tech-001.png")}},
        {"id": "missing", "input": {"type": "path", "path": str(FIXTURES / "images/nope.png")}},
    ]
    response = ko_en_runtime.handle({"protocol_version": "1", "operation": "ocr_batch", "items": items})
    result = response["result"]
    assert [item["id"] for item in result["items"]] == ["en", "ko", "mix", "missing"]
    assert [item["ok"] for item in result["items"]] == [True, True, True, False]
    assert result["items"][3]["error"]["code"] == "IMAGE_NOT_FOUND"
    assert "저장하기" in result["items"][1]["result"]["text"]
    assert "CUDA" in result["items"][2]["result"]["text"]


@needs_korean
def test_stdio_korean_round_trip(ko_en_runtime) -> None:
    from textj.transport.stdio import serve_stdio

    line = json.dumps({
        "protocol_version": "1", "operation": "ocr",
        "input": {"type": "path", "path": str(FIXTURES / "images/ko-ui-001.png")},
    })
    stdout = io.BytesIO()
    serve_stdio(ko_en_runtime, io.BytesIO(line.encode() + b"\n"), stdout)
    result = json.loads(stdout.getvalue().decode("utf-8"))["result"]
    assert "저장하기" in result["text"]
    assert all(line["box"] and 0 < line["score"] <= 1 for line in result["lines"])


def run_mcp(image: str, *args: str) -> tuple[dict, str]:
    """Run textj-mcp as a real subprocess: initialize -> ocr_image(image)."""
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "ocr_image", "arguments": {"path": str(FIXTURES / image)}}},
    ]
    stdin = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in messages).encode("utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "textj.adapters.mcp_server", *args],
        input=stdin, capture_output=True, timeout=300,
        # Hostile console encoding: protocol bytes must still be UTF-8.
        env={**os.environ, "PYTHONIOENCODING": "cp949" if os.name == "nt" else "latin-1"},
    )
    responses = [json.loads(line) for line in completed.stdout.decode("utf-8").splitlines()]
    call = next(r for r in responses if r.get("id") == 2)["result"]
    return call, completed.stderr.decode("utf-8", "replace")


def test_mcp_subprocess_english_end_to_end() -> None:
    call, stderr = run_mcp("images/en-url-001.png", "--language", "en", "--profile", "ppocrv6-small")
    assert call["isError"] is False, stderr
    structured = call["structuredContent"]["result"]
    assert "https://example.com/docs/api/v1" in structured["text"]
    assert json.loads(call["content"][0]["text"])["result"]["text"] == structured["text"]


@needs_korean
def test_mcp_subprocess_korean_end_to_end() -> None:
    call, stderr = run_mcp("images/mix-tech-001.png", "--language", "ko-en")
    assert call["isError"] is False, stderr
    structured = call["structuredContent"]["result"]
    assert "설정에서" in structured["text"] and "CUDA" in structured["text"]
    assert json.loads(call["content"][0]["text"])["result"]["text"] == structured["text"]
    assert all(line["box"] is not None for line in structured["lines"])
