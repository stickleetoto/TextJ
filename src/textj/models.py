from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

Point = tuple[float, float]
Box = tuple[Point, Point, Point, Point]


@dataclass(frozen=True, slots=True)
class OCRLine:
    """One recognized text region."""

    text: str
    score: float
    box: Box | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "score": self.score,
            "box": [list(point) for point in self.box] if self.box else None,
        }


@dataclass(frozen=True, slots=True)
class OCRResult:
    """Backend-independent OCR result returned by TextJ."""

    lines: tuple[OCRLine, ...]
    backend: str
    total_ms: float
    stages_ms: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text)

    @property
    def mean_score(self) -> float:
        if not self.lines:
            return 0.0
        return sum(line.score for line in self.lines) / len(self.lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "backend": self.backend,
            "total_ms": round(self.total_ms, 3),
            "mean_score": round(self.mean_score, 6),
            "stages_ms": {
                key: round(value, 3) for key, value in self.stages_ms.items()
            },
            "metadata": dict(self.metadata),
            "lines": [line.to_dict() for line in self.lines],
        }
