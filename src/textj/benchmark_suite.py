from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any

from textj.accuracy import character_error_rate
from textj.benchmark import BenchmarkSummary, run_benchmark
from textj.pipeline import OCRPipeline


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    image: Path
    expected: Path | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseResult:
    case: BenchmarkCase
    summary: BenchmarkSummary
    recognized_text: str
    cer: float | None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.case.case_id,
            "image": str(self.case.image),
            "expected": str(self.case.expected) if self.case.expected else None,
            "tags": list(self.case.tags),
            "recognized_text": self.recognized_text,
            "cer": round(self.cer, 6) if self.cer is not None else None,
            "benchmark": self.summary.to_dict(),
        }
        return payload


@dataclass(frozen=True, slots=True)
class SuiteResult:
    manifest: Path
    cases: tuple[CaseResult, ...]

    @property
    def mean_cer(self) -> float | None:
        values = [case.cer for case in self.cases if case.cer is not None]
        return fmean(values) if values else None

    @property
    def mean_p50_ms(self) -> float:
        if not self.cases:
            return 0.0
        return fmean(case.summary.p50_ms for case in self.cases)

    @property
    def mean_p95_ms(self) -> float:
        if not self.cases:
            return 0.0
        return fmean(case.summary.p95_ms for case in self.cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": str(self.manifest),
            "case_count": len(self.cases),
            "mean_cer": round(self.mean_cer, 6) if self.mean_cer is not None else None,
            "mean_p50_ms": round(self.mean_p50_ms, 3),
            "mean_p95_ms": round(self.mean_p95_ms, 3),
            "cases": [case.to_dict() for case in self.cases],
        }


def load_manifest(path: str | Path) -> tuple[BenchmarkCase, ...]:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("benchmark manifest must contain a non-empty 'cases' list")

    base = manifest.parent
    cases: list[BenchmarkCase] = []

    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise ValueError(f"case {index} must be an object")

        case_id = str(raw.get("id") or f"case-{index + 1}")
        image_value = raw.get("image")
        if not image_value:
            raise ValueError(f"case '{case_id}' is missing image")

        image = (base / str(image_value)).resolve()
        expected_value = raw.get("expected")
        expected = (base / str(expected_value)).resolve() if expected_value else None

        tags_value = raw.get("tags", [])
        if not isinstance(tags_value, list):
            raise ValueError(f"case '{case_id}' tags must be a list")

        cases.append(
            BenchmarkCase(
                case_id=case_id,
                image=image,
                expected=expected,
                tags=tuple(str(tag) for tag in tags_value),
            )
        )

    return tuple(cases)


def run_suite(
    pipeline: OCRPipeline,
    manifest_path: str | Path,
    *,
    runs: int = 10,
    warmups: int = 1,
    tags: tuple[str, ...] = (),
) -> SuiteResult:
    manifest = Path(manifest_path).resolve()
    cases = load_manifest(manifest)
    if tags:
        wanted = set(tags)
        cases = tuple(case for case in cases if wanted & set(case.tags))
        if not cases:
            raise ValueError(f"no benchmark cases match tags: {', '.join(tags)}")
    results: list[CaseResult] = []

    for case in cases:
        summary = run_benchmark(
            pipeline,
            case.image,
            runs=runs,
            warmups=warmups,
        )

        final = pipeline.run(case.image)
        expected_text = (
            case.expected.read_text(encoding="utf-8")
            if case.expected is not None
            else None
        )
        cer = (
            character_error_rate(expected_text, final.text)
            if expected_text is not None
            else None
        )

        results.append(
            CaseResult(
                case=case,
                summary=summary,
                recognized_text=final.text,
                cer=cer,
            )
        )

    return SuiteResult(manifest=manifest, cases=tuple(results))
