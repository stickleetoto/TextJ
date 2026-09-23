from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Sequence

from textj.pipeline import OCRPipeline


def percentile(values: Sequence[float], q: float) -> float:
    """Return an interpolated percentile for q in the inclusive range 0..1."""
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")

    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    backend: str
    runs: int
    warmups: int
    latencies_ms: tuple[float, ...]
    mean_score: float
    line_count: int
    metadata: dict[str, Any]

    @property
    def p50_ms(self) -> float:
        return median(self.latencies_ms)

    @property
    def p95_ms(self) -> float:
        return percentile(self.latencies_ms, 0.95)

    @property
    def minimum_ms(self) -> float:
        return min(self.latencies_ms)

    @property
    def maximum_ms(self) -> float:
        return max(self.latencies_ms)

    @property
    def mean_ms(self) -> float:
        return sum(self.latencies_ms) / len(self.latencies_ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "runs": self.runs,
            "warmups": self.warmups,
            "latency_ms": {
                "min": round(self.minimum_ms, 3),
                "mean": round(self.mean_ms, 3),
                "p50": round(self.p50_ms, 3),
                "p95": round(self.p95_ms, 3),
                "max": round(self.maximum_ms, 3),
            },
            "mean_score": round(self.mean_score, 6),
            "line_count": self.line_count,
            "metadata": self.metadata,
            "samples_ms": [round(value, 3) for value in self.latencies_ms],
        }


def run_benchmark(
    pipeline: OCRPipeline,
    image_path: str | Path,
    *,
    runs: int = 20,
    warmups: int = 2,
) -> BenchmarkSummary:
    if runs < 1:
        raise ValueError("runs must be at least 1")
    if warmups < 0:
        raise ValueError("warmups cannot be negative")

    for _ in range(warmups):
        pipeline.run(image_path)

    samples: list[float] = []
    last_result = None

    for _ in range(runs):
        last_result = pipeline.run(image_path)
        samples.append(last_result.total_ms)

    assert last_result is not None

    return BenchmarkSummary(
        backend=last_result.backend,
        runs=runs,
        warmups=warmups,
        latencies_ms=tuple(samples),
        mean_score=last_result.mean_score,
        line_count=len(last_result.lines),
        metadata=dict(last_result.metadata),
    )
