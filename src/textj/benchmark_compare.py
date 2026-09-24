"""Compare two TextJ benchmark artifacts and flag regressions.

Accepts either ``textj-bench`` (single image) or ``textj-bench-suite`` JSON.
Metrics are reported separately; there is deliberately no combined score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

METRICS = ("p50_ms", "p95_ms", "cer", "rss_mb")


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Regression limits. ``None`` disables a check."""

    max_p50_regression_pct: float | None = None
    max_p95_regression_pct: float | None = None
    max_cer_increase: float | None = None
    max_rss_increase_mb: float | None = None


@dataclass(frozen=True, slots=True)
class MetricDelta:
    scope: str
    metric: str
    baseline: float | None
    candidate: float | None
    failed: bool = False

    @property
    def delta(self) -> float | None:
        if self.baseline is None or self.candidate is None:
            return None
        return self.candidate - self.baseline

    @property
    def delta_pct(self) -> float | None:
        if self.delta is None or not self.baseline:
            return None
        return self.delta / self.baseline * 100.0

    def to_dict(self) -> dict[str, Any]:
        def rounded(value: float | None) -> float | None:
            return round(value, 6) if value is not None else None

        return {
            "scope": self.scope,
            "metric": self.metric,
            "baseline": rounded(self.baseline),
            "candidate": rounded(self.candidate),
            "delta": rounded(self.delta),
            "delta_pct": rounded(self.delta_pct),
            "failed": self.failed,
        }


@dataclass(frozen=True, slots=True)
class Comparison:
    deltas: tuple[MetricDelta, ...]
    missing_cases: tuple[str, ...]
    new_cases: tuple[str, ...]

    @property
    def failed(self) -> bool:
        return any(delta.failed for delta in self.deltas)

    def to_dict(self) -> dict[str, Any]:
        return {
            "failed": self.failed,
            "missing_cases": list(self.missing_cases),
            "new_cases": list(self.new_cases),
            "deltas": [delta.to_dict() for delta in self.deltas],
        }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _single_metrics(payload: Mapping[str, Any]) -> dict[str, float | None]:
    latency = payload.get("latency_ms") or {}
    memory = payload.get("memory_mb") or {}
    return {
        "p50_ms": _number(latency.get("p50")),
        "p95_ms": _number(latency.get("p95")),
        "cer": _number(payload.get("cer")),
        "rss_mb": _number(memory.get("sampled_peak_rss")),
    }


def extract_metrics(
    payload: Mapping[str, Any],
) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
    """Return (aggregate metrics, per-case metrics) for a benchmark artifact."""
    if "cases" in payload:
        cases: dict[str, dict[str, float | None]] = {}
        for case in payload.get("cases") or []:
            metrics = _single_metrics(case.get("benchmark") or {})
            metrics["cer"] = _number(case.get("cer"))
            cases[str(case.get("id"))] = metrics
        rss_values = [m["rss_mb"] for k, m in cases.items()
                      if m["rss_mb"] is not None and not k.startswith("tag:")]
        for tag, agg in (payload.get("by_tag") or {}).items():
            cases[f"tag:{tag}"] = {
                "p50_ms": _number(agg.get("mean_p50_ms")),
                "p95_ms": _number(agg.get("mean_p95_ms")),
                "cer": _number(agg.get("mean_cer")),
                "rss_mb": _number(agg.get("max_sampled_rss_mb")),
            }
        aggregate = {
            "p50_ms": _number(payload.get("mean_p50_ms")),
            "p95_ms": _number(payload.get("mean_p95_ms")),
            "cer": _number(payload.get("mean_cer")),
            "rss_mb": max(rss_values) if rss_values else None,
        }
        return aggregate, cases

    if "latency_ms" in payload:
        return _single_metrics(payload), {}

    raise ValueError("unrecognized benchmark artifact: expected 'latency_ms' or 'cases'")


def _check(metric: str, baseline: float | None, candidate: float | None,
           thresholds: Thresholds) -> bool:
    if baseline is None or candidate is None:
        return False
    delta = candidate - baseline
    if metric == "p50_ms" and thresholds.max_p50_regression_pct is not None:
        return baseline > 0 and delta / baseline * 100.0 > thresholds.max_p50_regression_pct
    if metric == "p95_ms" and thresholds.max_p95_regression_pct is not None:
        return baseline > 0 and delta / baseline * 100.0 > thresholds.max_p95_regression_pct
    if metric == "cer" and thresholds.max_cer_increase is not None:
        return delta > thresholds.max_cer_increase
    if metric == "rss_mb" and thresholds.max_rss_increase_mb is not None:
        return delta > thresholds.max_rss_increase_mb
    return False


def compare(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    thresholds: Thresholds = Thresholds(),
) -> Comparison:
    base_agg, base_cases = extract_metrics(baseline)
    cand_agg, cand_cases = extract_metrics(candidate)

    deltas: list[MetricDelta] = []

    def add(scope: str, base: Mapping[str, float | None],
            cand: Mapping[str, float | None]) -> None:
        for metric in METRICS:
            b, c = base.get(metric), cand.get(metric)
            deltas.append(
                MetricDelta(scope, metric, b, c, _check(metric, b, c, thresholds))
            )

    add("aggregate", base_agg, cand_agg)
    for case_id in base_cases:
        if case_id in cand_cases:
            scope = case_id if case_id.startswith("tag:") else f"case:{case_id}"
            add(scope, base_cases[case_id], cand_cases[case_id])

    return Comparison(
        deltas=tuple(deltas),
        missing_cases=tuple(c for c in base_cases if c not in cand_cases and not c.startswith("tag:")),
        new_cases=tuple(c for c in cand_cases if c not in base_cases and not c.startswith("tag:")),
    )


def format_comparison(comparison: Comparison) -> str:
    lines = ["TextJ benchmark comparison"]
    header = f"  {'scope':<28} {'metric':<8} {'baseline':>12} {'candidate':>12} {'delta':>12} {'delta%':>8}"
    lines.append(header)

    def fmt(value: float | None, digits: int) -> str:
        return f"{value:.{digits}f}" if value is not None else "-"

    for d in comparison.deltas:
        digits = 4 if d.metric == "cer" else 1
        flag = "  FAIL" if d.failed else ""
        lines.append(
            f"  {d.scope:<28} {d.metric:<8} {fmt(d.baseline, digits):>12} "
            f"{fmt(d.candidate, digits):>12} {fmt(d.delta, digits):>12} "
            f"{fmt(d.delta_pct, 1):>8}{flag}"
        )
    if comparison.missing_cases:
        lines.append(f"  missing cases: {', '.join(comparison.missing_cases)}")
    if comparison.new_cases:
        lines.append(f"  new cases: {', '.join(comparison.new_cases)}")
    lines.append(f"  result: {'REGRESSION' if comparison.failed else 'ok'}")
    return "\n".join(lines)
