import json
from pathlib import Path

import pytest

from textj.app.bench_compare import main
from textj.benchmark_compare import Thresholds, compare, extract_metrics


def single(p50: float, p95: float, cer: float | None, rss: float) -> dict:
    return {
        "latency_ms": {"p50": p50, "p95": p95},
        "memory_mb": {"sampled_peak_rss": rss},
        "cer": cer,
    }


def suite(cases: dict[str, tuple[float, float, float]]) -> dict:
    return {
        "mean_p50_ms": sum(c[0] for c in cases.values()) / len(cases),
        "mean_p95_ms": sum(c[1] for c in cases.values()) / len(cases),
        "mean_cer": sum(c[2] for c in cases.values()) / len(cases),
        "cases": [
            {"id": case_id, "cer": c[2], "benchmark": single(c[0], c[1], None, 100.0)}
            for case_id, c in cases.items()
        ],
    }


def test_single_artifact_deltas() -> None:
    result = compare(single(100, 120, 0.1, 200), single(110, 150, 0.05, 210))
    by_metric = {d.metric: d for d in result.deltas}
    assert by_metric["p50_ms"].delta == 10
    assert by_metric["p50_ms"].delta_pct == pytest.approx(10.0)
    assert by_metric["cer"].delta == pytest.approx(-0.05)
    assert by_metric["rss_mb"].delta == 10
    assert not result.failed


def test_thresholds_flag_regressions() -> None:
    thresholds = Thresholds(max_p95_regression_pct=20, max_cer_increase=0.01)
    result = compare(single(100, 100, 0.1, 200), single(100, 125, 0.1, 200), thresholds)
    assert result.failed
    assert [d.metric for d in result.deltas if d.failed] == ["p95_ms"]

    result = compare(single(100, 100, 0.1, 200), single(100, 100, 0.2, 200), thresholds)
    assert [d.metric for d in result.deltas if d.failed] == ["cer"]


def test_missing_values_never_fail() -> None:
    result = compare(
        single(100, 100, None, 200),
        single(100, 100, 0.5, 200),
        Thresholds(max_cer_increase=0.0),
    )
    assert not result.failed


def test_suite_per_case_and_case_set_changes() -> None:
    base = suite({"a": (10, 12, 0.0), "b": (20, 25, 0.1)})
    cand = suite({"a": (10, 30, 0.0), "c": (5, 5, 0.0)})
    result = compare(base, cand, Thresholds(max_p95_regression_pct=50))
    assert result.missing_cases == ("b",)
    assert result.new_cases == ("c",)
    failed_scopes = {d.scope for d in result.deltas if d.failed}
    assert "case:a" in failed_scopes


def test_rejects_unknown_artifact() -> None:
    with pytest.raises(ValueError):
        extract_metrics({"hello": 1})


def test_cli_exit_codes(tmp_path: Path, capsys) -> None:
    base = tmp_path / "base.json"
    cand = tmp_path / "cand.json"
    base.write_text(json.dumps(single(100, 100, 0.0, 100)), encoding="utf-8")
    cand.write_text(json.dumps(single(200, 200, 0.0, 100)), encoding="utf-8")

    assert main([str(base), str(cand)]) == 0
    assert main([str(base), str(cand), "--max-p50-regression-pct", "10"]) == 1
    assert main([str(base), str(cand), "--json"]) == 0
    assert main([str(base), str(tmp_path / "missing.json")]) == 2


def test_cli_json_output(tmp_path: Path, capsys) -> None:
    base = tmp_path / "base.json"
    base.write_text(json.dumps(single(100, 100, 0.0, 100)), encoding="utf-8")
    assert main([str(base), str(base), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["failed"] is False
    assert payload["deltas"][0]["metric"] == "p50_ms"
