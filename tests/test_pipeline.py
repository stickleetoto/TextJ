from pathlib import Path

import pytest

from textj.backends.base import BackendResult, OCRBackend
from textj.models import OCRLine
from textj.pipeline import OCRPipeline


class FakeBackend(OCRBackend):
    name = "fake"

    def recognize(self, image_path: Path) -> BackendResult:
        return BackendResult(
            lines=(
                OCRLine(text="TextJ", score=0.99),
                OCRLine(text="빠른 OCR", score=0.80),
            ),
            metadata={
                "engine_stages_ms": {
                    "detect": 1.0,
                    "classify": 0.0,
                    "recognize": 2.0,
                }
            },
        )


def test_pipeline_runs_backend_and_merges_stage_timings(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake")

    result = OCRPipeline(FakeBackend()).run(image)

    assert result.backend == "fake"
    assert result.text == "TextJ\n빠른 OCR"
    assert result.stages_ms["engine_detect"] == 1.0
    assert result.stages_ms["engine_recognize"] == 2.0
    assert result.total_ms >= 0.0


def test_pipeline_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OCRPipeline(FakeBackend()).run(tmp_path / "missing.png")
