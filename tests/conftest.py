from __future__ import annotations

import base64
import io
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from textj.backends.base import BackendResult, OCRBackend
from textj.models import OCRLine
from textj.runtime import RuntimeConfig, TextJRuntime


class ControllableBackend(OCRBackend):
    """Fake OCR backend for protocol/runtime tests (no models required)."""

    name = "fake"

    def __init__(self, *, delay: float = 0.0, fail: bool = False,
                 gate: threading.Event | None = None) -> None:
        self.delay = delay
        self.fail = fail
        self.gate = gate
        self.calls = 0
        self.shapes: list[tuple[int, ...]] = []
        self.closed = False

    def recognize(self, image) -> BackendResult:
        self.calls += 1
        self.shapes.append(tuple(image.shape))
        if self.gate is not None:
            self.gate.wait(5)
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("engine exploded")
        return BackendResult(
            lines=(
                OCRLine("안녕하세요 TextJ", 0.97, ((1.0, 2.0), (30.0, 2.0), (30.0, 9.0), (1.0, 9.0))),
                OCRLine("low", 0.2, None),
            ),
            metadata={"engine_stages_ms": {"detect": 1.5, "classify": None, "recognize": 2.5}},
        )

    def close(self) -> None:
        self.closed = True


def png_bytes(width: int = 40, height: int = 20, mode: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    color = (255, 255, 255, 255) if mode == "RGBA" else "white"
    Image.new(mode, (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@pytest.fixture
def png_path(tmp_path: Path) -> Path:
    path = tmp_path / "image.png"
    path.write_bytes(png_bytes())
    return path


@pytest.fixture
def make_runtime():
    runtimes: list[TextJRuntime] = []

    def factory(backend: OCRBackend | None = None, **config) -> TextJRuntime:
        backends = [backend] if backend is not None else []

        def build() -> OCRBackend:
            return backends.pop() if backends else ControllableBackend()

        runtime = TextJRuntime(RuntimeConfig(**config), backend_factory=build)
        runtime.start()
        runtimes.append(runtime)
        return runtime

    yield factory
    for runtime in runtimes:
        runtime.close(timeout=5)


def request(operation: str = "ocr", **fields) -> dict:
    return {"protocol_version": "1", "operation": operation, **fields}
