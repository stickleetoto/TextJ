import json
from pathlib import Path

from textj.backends.base import BackendResult, OCRBackend
from textj.benchmark_suite import load_manifest, run_suite
from textj.models import OCRLine
from textj.pipeline import OCRPipeline


class FakeBackend(OCRBackend):
    name = "fake"

    def recognize(self, image_path: Path) -> BackendResult:
        return BackendResult(
            lines=(OCRLine(text="안녕하세요 TextJ", score=1.0),),
            metadata={"fixture": True},
        )


def test_load_manifest_resolves_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"fake")
    (tmp_path / "expected.txt").write_text("안녕하세요 TextJ", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "cases": [{
                "id": "ko-1",
                "image": "image.png",
                "expected": "expected.txt",
                "tags": ["KO", "UI"],
            }]
        }),
        encoding="utf-8",
    )

    cases = load_manifest(manifest)

    assert cases[0].case_id == "ko-1"
    assert cases[0].image == (tmp_path / "image.png").resolve()
    assert cases[0].tags == ("KO", "UI")


def test_suite_calculates_cer(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"fake")
    (tmp_path / "expected.txt").write_text("안녕하세요 TextJ", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "cases": [{
                "id": "ko-1",
                "image": "image.png",
                "expected": "expected.txt",
            }]
        }),
        encoding="utf-8",
    )

    result = run_suite(
        OCRPipeline(FakeBackend()),
        manifest,
        runs=2,
        warmups=0,
    )

    assert result.mean_cer == 0.0
    assert result.cases[0].cer == 0.0
    assert result.cases[0].recognized_text == "안녕하세요 TextJ"


def test_suite_tag_filter(tmp_path: Path) -> None:
    import pytest

    (tmp_path / "image.png").write_bytes(b"fake")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"cases": [
        {"id": "ko", "image": "image.png", "tags": ["KO"]},
        {"id": "en", "image": "image.png", "tags": ["EN", "UI"]},
    ]}), encoding="utf-8")

    result = run_suite(OCRPipeline(FakeBackend()), manifest, runs=1, warmups=0, tags=("UI",))
    assert [case.case.case_id for case in result.cases] == ["en"]
    with pytest.raises(ValueError):
        run_suite(OCRPipeline(FakeBackend()), manifest, runs=1, warmups=0, tags=("XX",))


def test_suite_by_tag_aggregates(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"fake")
    (tmp_path / "good.txt").write_text("안녕하세요 TextJ", encoding="utf-8")
    (tmp_path / "bad.txt").write_text("완전히 다른 문장", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"cases": [
        {"id": "ko", "image": "image.png", "expected": "bad.txt", "tags": ["KO"]},
        {"id": "mix", "image": "image.png", "expected": "good.txt", "tags": ["MIX", "UI"]},
    ]}), encoding="utf-8")

    payload = run_suite(OCRPipeline(FakeBackend()), manifest, runs=1, warmups=0).to_dict()

    assert set(payload["by_tag"]) == {"KO", "MIX", "UI"}
    assert payload["by_tag"]["MIX"]["mean_cer"] == 0.0
    assert payload["by_tag"]["KO"]["mean_cer"] > 0.5
    assert payload["by_tag"]["KO"]["case_count"] == 1
