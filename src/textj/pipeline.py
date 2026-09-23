from __future__ import annotations

from pathlib import Path
from time import perf_counter

from textj.backends.base import OCRBackend
from textj.models import OCRResult


class OCRPipeline:
    """Small v0.1 pipeline that owns end-to-end timing."""

    def __init__(self, backend: OCRBackend) -> None:
        self.backend = backend

    def run(self, image_path: str | Path) -> OCRResult:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        total_start = perf_counter()

        backend_start = perf_counter()
        backend_result = self.backend.recognize(path)
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

        return OCRResult(
            lines=backend_result.lines,
            backend=self.backend.name,
            total_ms=total_ms,
            stages_ms=stages,
            metadata=backend_result.metadata,
        )
