from textj.models import OCRLine, OCRResult


def test_result_text_and_mean_score() -> None:
    result = OCRResult(
        lines=(
            OCRLine(text="안녕하세요", score=0.9),
            OCRLine(text="TextJ", score=0.7),
        ),
        backend="test",
        total_ms=12.3456,
    )

    assert result.text == "안녕하세요\nTextJ"
    assert result.mean_score == 0.8


def test_result_serialization_keeps_unicode_and_box() -> None:
    result = OCRResult(
        lines=(
            OCRLine(
                text="한글 OCR",
                score=0.95,
                box=((0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)),
            ),
        ),
        backend="test",
        total_ms=1.23456,
        stages_ms={"backend": 1.0},
    )

    payload = result.to_dict()

    assert payload["text"] == "한글 OCR"
    assert payload["total_ms"] == 1.235
    assert payload["lines"][0]["box"][2] == [10.0, 5.0]
