from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np

from textj.backends.base import OCRBackend
from textj.image_types import OCRInput
from textj.models import OCRResult


class OCRPipeline:
    """Small OCR pipeline that owns validation and end-to-end timing."""

    def __init__(self, backend: OCRBackend) -> None:
        self.backend = backend

    def run(self, image: str | Path | np.ndarray) -> OCRResult:
        total_start = perf_counter()

        backend_input, input_kind = _normalize_input(image)

        backend_start = perf_counter()
        backend_result = self.backend.recognize(backend_input)
        backend_ms = (perf_counter() - backend_start) * 1000.0

        total_ms = (perf_counter() - total_start) * 1000.0

        stages = {
            "backend": backend_ms,
        }

        engine_stages = backend_result.metadata.get("engine_stages_ms")
        if isinstance(engine_stages, dict):
            for key, value in engine_stages.items():
                if isinstance(value, (int, float)):
                    stages[f"engine_{key}"] = float(value)

        metadata = dict(backend_result.metadata)
        metadata["input_kind"] = input_kind

        return OCRResult(
            lines=backend_result.lines,
            backend=self.backend.name,
            total_ms=total_ms,
            stages_ms=stages,
            metadata=metadata,
        )


def _normalize_input(image: str | Path | np.ndarray) -> tuple[OCRInput, str]:
    if isinstance(image, np.ndarray):
        if image.size == 0:
            raise ValueError("Image array is empty")
        if image.ndim not in (2, 3):
            raise ValueError(
                f"Image array must have 2 or 3 dimensions, got {image.ndim}"
            )
        return image, "ndarray"

    path = Path(image)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    return path, "path"
