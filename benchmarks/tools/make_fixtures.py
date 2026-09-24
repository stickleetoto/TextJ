"""Generate the synthetic TextJ benchmark fixture corpus.

Fixtures are rendered text with known ground truth, so they are safe to commit
(no private screenshots, no copyrighted content). The generated PNGs are
committed; re-running this script with different fonts changes pixels, so only
regenerate deliberately and re-baseline benchmarks afterwards.

Usage:
    python benchmarks/tools/make_fixtures.py \
        --sans /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
        --mono /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf \
        --korean /path/to/NanumGothic.ttf

Fonts used for the committed corpus: DejaVu Sans / DejaVu Sans Mono
(Bitstream Vera license) and NanumGothic (SIL OFL 1.1).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "fixtures"


@dataclass(frozen=True)
class Case:
    case_id: str
    tags: tuple[str, ...]
    lines: tuple[str, ...]
    font: str  # "sans" | "mono" | "korean"
    size: int
    fg: tuple[int, int, int] = (20, 20, 20)
    bg: tuple[int, int, int] = (255, 255, 255)
    padding: int = 16
    spacing: float = 1.5
    # Optional fixed canvas with one (x, y) position per line: screen-like layout.
    canvas: tuple[int, int] | None = None
    positions: tuple[tuple[int, int], ...] = ()


CASES = (
    Case("en-ui-001", ("EN", "UI", "S"), ("Save changes", "Cancel"), "sans", 20),
    Case("en-para-001", ("EN", "M"), (
        "TextJ is a local OCR tool for AI agents.",
        "It returns text, confidence scores and boxes.",
        "Latency is measured from request to response.",
    ), "sans", 22),
    Case("en-url-001", ("EN", "URL", "S"), (
        "https://example.com/docs/api/v1?lang=en&page=2",
        "C:/Users/agent/Documents/report_2026-09.pdf",
    ), "sans", 20),
    Case("code-py-001", ("CODE", "M"), (
        "def load_image(path: str) -> np.ndarray:",
        "    data = Path(path).read_bytes()",
        "    return cv2.imdecode(data, 1)",
    ), "mono", 18),
    Case("term-dark-001", ("TERM", "DARK", "M"), (
        "$ pytest -q",
        "95 passed in 1.84s",
        "$ git status --short",
        "M src/textj/runtime/runtime.py",
    ), "mono", 18, fg=(210, 210, 210), bg=(30, 30, 30)),
    Case("dark-ui-001", ("DARK", "UI", "S"), (
        "Settings",
        "Enable notifications",
    ), "sans", 20, fg=(235, 235, 235), bg=(40, 44, 52)),
    Case("tiny-en-001", ("TINY", "EN", "S"), (
        "Last updated 2026-09-24 09:41",
        "Version 0.1.0.dev0 build 964db73",
    ), "sans", 11, padding=6),
    Case("screen-en-001", ("EN", "UI", "L"), (
        "File   Edit   View   Help",
        "Project settings",
        "Name: textj-runtime",
        "Max queue: 8",
        "Status: ready",
        "Apply",
    ), "sans", 18, canvas=(1280, 720), positions=(
        (16, 12), (80, 120), (80, 180), (80, 220), (80, 260), (1100, 660),
    )),
    Case("ko-ui-001", ("KO", "UI", "S"), ("저장하기", "취소"), "korean", 22),
    Case("ko-para-001", ("KO", "M"), (
        "텍스트제이는 인공지능 에이전트를 위한 로컬 OCR 도구입니다.",
        "결과에는 텍스트, 신뢰도, 좌표가 포함됩니다.",
    ), "korean", 22),
    Case("mix-ui-001", ("MIX", "UI", "M"), (
        "파일 경로: C:/Users/test/문서/report.txt",
        "오류 코드 IMAGE_NOT_FOUND 발생",
        "다운로드 속도 12.5 MB/s",
    ), "korean", 20),
)


def render(case: Case, fonts: dict[str, Path]) -> Image.Image:
    font = ImageFont.truetype(str(fonts[case.font]), case.size)
    if case.canvas is not None:
        image = Image.new("RGB", case.canvas, case.bg)
        draw = ImageDraw.Draw(image)
        for line, position in zip(case.lines, case.positions, strict=True):
            draw.text(position, line, font=font, fill=case.fg)
        return image
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [probe.textlength(line, font=font) for line in case.lines]
    line_height = int(case.size * case.spacing)
    width = int(max(widths)) + 2 * case.padding
    height = line_height * len(case.lines) + 2 * case.padding
    image = Image.new("RGB", (width, height), case.bg)
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(case.lines):
        draw.text((case.padding, case.padding + index * line_height), line, font=font, fill=case.fg)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sans", type=Path, default=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    parser.add_argument("--mono", type=Path, default=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
    parser.add_argument("--korean", type=Path, help="Font with Hangul glyphs (e.g. NanumGothic.ttf).")
    parser.add_argument("--out", type=Path, default=ROOT)
    args = parser.parse_args()

    fonts = {"sans": args.sans, "mono": args.mono}
    if args.korean:
        fonts["korean"] = args.korean

    (args.out / "images").mkdir(parents=True, exist_ok=True)
    (args.out / "expected").mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in CASES:
        if case.font not in fonts:
            print(f"skip {case.case_id}: no {case.font} font given")
            continue
        image_rel = f"images/{case.case_id}.png"
        expected_rel = f"expected/{case.case_id}.txt"
        render(case, fonts).save(args.out / image_rel, optimize=True)
        (args.out / expected_rel).write_text("\n".join(case.lines) + "\n", encoding="utf-8")
        manifest.append({
            "id": case.case_id,
            "image": image_rel,
            "expected": expected_rel,
            "tags": list(case.tags),
        })
        print(f"wrote {case.case_id}")

    (args.out / "manifest.json").write_text(
        json.dumps({"cases": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
