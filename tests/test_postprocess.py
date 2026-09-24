from textj.models import OCRLine
from textj.postprocess import indented_text


def box(left: float, top: float, width: float, height: float = 10.0):
    return ((left, top), (left + width, top), (left + width, top + height), (left, top + height))


def test_restores_indentation_for_monospace_lines() -> None:
    # 10 px per character
    lines = (
        OCRLine("def f():", 0.9, box(20, 0, 80)),
        OCRLine("return 1", 0.9, box(60, 20, 80)),
        OCRLine("x = 2", 0.9, box(20, 40, 50)),
    )
    assert indented_text(lines) == "def f():\n    return 1\nx = 2"


def test_lines_without_boxes_are_not_indented() -> None:
    lines = (OCRLine("a", 0.9, None), OCRLine("bb", 0.9, box(30, 0, 20)), OCRLine("", 0.9, None))
    assert indented_text(lines) == "a\nbb"
    assert indented_text((OCRLine("x", 1.0, None),)) == "x"
