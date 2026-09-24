"""Backend-independent text postprocessing."""

from __future__ import annotations

from statistics import median
from typing import Sequence

from textj.models import OCRLine


def indented_text(lines: Sequence[OCRLine]) -> str:
    """Join lines, restoring leading indentation from box geometry.

    Recognizers drop leading whitespace. For monospaced text (code, terminals)
    the left edge of each line box still encodes indentation, so each line is
    prefixed with ``round((left - min_left) / char_width)`` spaces, where
    ``char_width`` is the median of box width / character count over lines.
    Lines without boxes are left unchanged. Line order is not modified.
    """
    geometry = []
    for line in lines:
        if line.box is None or not line.text:
            geometry.append(None)
            continue
        xs = [point[0] for point in line.box]
        left, right = min(xs), max(xs)
        geometry.append((left, right - left))

    measured = [(left, width, len(line.text)) for line, geo in zip(lines, geometry)
                if geo is not None for left, width in [geo]]
    if not measured:
        return "\n".join(line.text for line in lines if line.text)

    char_width = median(width / count for _, width, count in measured if count > 0)
    min_left = min(left for left, _, _ in measured)

    output = []
    for line, geo in zip(lines, geometry):
        if not line.text:
            continue
        indent = 0
        if geo is not None and char_width > 0:
            indent = max(0, round((geo[0] - min_left) / char_width))
        output.append(" " * indent + line.text)
    return "\n".join(output)
