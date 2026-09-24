"""Real OCR integration tests (opt-in): ``pytest -m integration``.

Uses the PP-OCRv6 small models bundled in the rapidocr wheel, so no download is
needed. Korean (ppocrv5-mobile) is covered only when TEXTJ_KOREAN_MODELS=1,
because it downloads models on first use.
"""

import json
import os
from pathlib import Path

import pytest

from textj.accuracy import character_error_rate

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"


def load_cases(tags):
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    return [case for case in manifest["cases"] if set(case["tags"]) & set(tags)]


@pytest.fixture(scope="module")
def english_runtime():
    pytest.importorskip("rapidocr")
    from textj.runtime import RuntimeConfig, TextJRuntime

    runtime = TextJRuntime(RuntimeConfig(language="en", profile="ppocrv6-small")).start()
    yield runtime
    runtime.close()


@pytest.mark.parametrize("case", load_cases({"EN", "CODE", "TERM", "DARK", "TINY"}), ids=lambda c: c["id"])
def test_english_fixture_cer(english_runtime, case) -> None:
    response = english_runtime.handle({
        "protocol_version": "1",
        "operation": "ocr",
        "input": {"type": "path", "path": str(FIXTURES / case["image"])},
    })
    assert response["ok"], response
    expected = (FIXTURES / case["expected"]).read_text(encoding="utf-8")
    # Loose bound: catches broken pipelines, not small accuracy shifts
    # (use textj-bench-compare for those).
    assert character_error_rate(expected, response["result"]["text"]) < 0.15


@pytest.mark.skipif(os.environ.get("TEXTJ_KOREAN_MODELS") != "1",
                    reason="set TEXTJ_KOREAN_MODELS=1 to download/use PP-OCRv5 Korean models")
@pytest.mark.parametrize("case", load_cases({"KO", "MIX"}), ids=lambda c: c["id"])
def test_korean_fixture_cer(case) -> None:
    from textj.runtime import RuntimeConfig, TextJRuntime

    with TextJRuntime(RuntimeConfig(language="korean")) as runtime:
        response = runtime.ocr(FIXTURES / case["image"])
    assert response["ok"], response
    expected = (FIXTURES / case["expected"]).read_text(encoding="utf-8")
    assert character_error_rate(expected, response["result"]["text"]) < 0.15
