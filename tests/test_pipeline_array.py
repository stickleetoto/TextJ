from pathlib import Path

import numpy as np
import pytest

from textj.backends.base import BackendResult, OCRBackend
from textj.image_types import OCRInput
from textj.models import OCRLine
from textj.pipeline import OCRPipeline


class ArrayBackend(OCRBackend):
    name = "array-fake"

    def recognize(self, image: OCRInput) -> BackendResult:
        assert isinstance(image, np.ndarray)
        return BackendResult(
            lines=(OCRLine(text="메모리 OCR", score=1.0),),
            metadata={},
        )


def test_pipeline_accepts_numpy_image() -> None:
    image = np.zeros((20, 40, 3), dtype=np.uint8)

    result = OCRPipeline(ArrayBackend()).run(image)

    assert result.text == "메모리 OCR"
    assert result.metadata["input_kind"] == "ndarray"


def test_pipeline_rejects_empty_numpy_image() -> None:
    image = np.array([], dtype=np.uint8)

    with pytest.raises(ValueError):
        OCRPipeline(ArrayBackend()).run(image)
