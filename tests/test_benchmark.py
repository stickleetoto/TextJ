from pathlib import Path

from textj.backends.base import BackendResult, OCRBackend
from textj.benchmark import percentile, run_benchmark
from textj.models import OCRLine
from textj.pipeline import OCRPipeline


class FakeBackend(OCRBackend):
    name = "fake"

    def recognize(self, image_path: Path) -> BackendResult:
        return BackendResult(
            lines=(OCRLine(text="TextJ", score=0.95),),
            metadata={"fixture": True},
        )


def test_percentile_interpolates() -> None:
    assert percentile([10.0, 20.0, 30.0], 0.5) == 20.0
    assert percentile([10.0, 20.0], 0.5) == 15.0


def test_benchmark_collects_requested_samples(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake")

    summary = run_benchmark(
        OCRPipeline(FakeBackend()),
        image,
        runs=5,
        warmups=2,
    )

    assert summary.runs == 5
    assert summary.warmups == 2
    assert len(summary.latencies_ms) == 5
    assert summary.backend == "fake"
    assert summary.line_count == 1
    assert summary.mean_score == 0.95
    assert summary.p95_ms >= summary.minimum_ms


def test_benchmark_records_image_dimensions(tmp_path: Path) -> None:
    from PIL import Image

    image = tmp_path / "sample.png"
    Image.new("RGB", (32, 16), "white").save(image)

    summary = run_benchmark(OCRPipeline(FakeBackend()), image, runs=1, warmups=0)

    assert summary.image["width"] == 32
    assert summary.image["height"] == 16
    assert summary.to_dict()["image"]["format"] == "PNG"


def test_system_info_has_version() -> None:
    from textj import __version__
    from textj.system_info import collect_system_info

    info = collect_system_info()
    assert info["textj_version"] == __version__
    assert "git_commit" in info
