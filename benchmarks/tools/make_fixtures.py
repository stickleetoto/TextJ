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
    Case("ko-num-001", ("KO", "NUM", "M"), (
        "2026년 9월 24일 오후 3시 15분",
        "총 1,234개 중 987개 완료 (80.0%)",
    ), "korean", 22),
    Case("ko-punct-001", ("KO", "PUNCT", "M"), (
        "정말요? 네, 맞습니다!",
        "\"확인\" 버튼을 누르세요. (필수)",
    ), "korean", 22),
    Case("ko-dark-001", ("KO", "DARK", "UI", "S"), (
        "알림 설정",
        "자동 업데이트 사용",
    ), "korean", 22, fg=(235, 235, 235), bg=(40, 44, 52)),
    Case("mix-tech-001", ("MIX", "TECH", "M"), (
        "설정에서 CUDA provider를 활성화하세요",
        "TextJ 서버 상태: READY",
    ), "korean", 22),
    Case("mix-path-001", ("MIX", "PATH", "M"), (
        "파일을 C:\\Users\\test\\model.onnx 에 저장했습니다",
        "로그 위치: /var/log/textj/server.log",
    ), "korean", 20),
    Case("mix-url-001", ("MIX", "URL", "M"), (
        "문서: https://example.com/docs/ko/v1",
        "자세한 내용은 github.com/example/textj 참고",
    ), "korean", 20),
    Case("mix-lib-001", ("MIX", "TECH", "M"), (
        "PyTorch 2.4와 ONNX Runtime 1.20을 설치합니다",
        "모델: PP-OCRv5 mobile, 백엔드: RapidOCR",
    ), "korean", 20),
    Case("mix-num-001", ("MIX", "NUM", "M"), (
        "응답 시간 p95 = 168.9 ms",
        "메모리 268 MB, 요청 40건 성공",
    ), "korean", 22),
    Case("mix-term-001", ("MIX", "TERM", "DARK", "M"), (
        "$ textj-client ocr 스크린샷.png",
        "오류: IMAGE_NOT_FOUND (재시도 불가)",
    ), "korean", 18, fg=(210, 210, 210), bg=(30, 30, 30)),
)


# Korean fonts such as NanumGothic draw U+005C (backslash) as the Won sign.
# These characters are drawn with the sans font so pixels match ground truth.
FALLBACK_CHARS = {"\\"}


def _segments(line: str) -> list[tuple[str, bool]]:
    """Split a line into (text, use_fallback) runs."""
    runs: list[tuple[str, bool]] = []
    for char in line:
        fallback = char in FALLBACK_CHARS
        if runs and runs[-1][1] == fallback:
            runs[-1] = (runs[-1][0] + char, fallback)
        else:
            runs.append((char, fallback))
    return runs


def _draw_line(draw, xy, line, font, fallback_font, fill) -> None:
    x, y = xy
    for text, use_fallback in _segments(line):
        run_font = fallback_font if use_fallback and fallback_font is not None else font
        draw.text((x, y), text, font=run_font, fill=fill)
        x += draw.textlength(text, font=run_font)


def _line_width(draw, line, font, fallback_font) -> float:
    return sum(
        draw.textlength(text, font=fallback_font if fb and fallback_font is not None else font)
        for text, fb in _segments(line)
    )


def render(case: Case, fonts: dict[str, Path]) -> Image.Image:
    font = ImageFont.truetype(str(fonts[case.font]), case.size)
    fallback = (
        ImageFont.truetype(str(fonts["sans"]), case.size) if case.font == "korean" else None
    )
    if case.canvas is not None:
        image = Image.new("RGB", case.canvas, case.bg)
        draw = ImageDraw.Draw(image)
        for line, position in zip(case.lines, case.positions, strict=True):
            _draw_line(draw, position, line, font, fallback, case.fg)
        return image
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [_line_width(probe, line, font, fallback) for line in case.lines]
    line_height = int(case.size * case.spacing)
    width = int(max(widths)) + 2 * case.padding
    height = line_height * len(case.lines) + 2 * case.padding
    image = Image.new("RGB", (width, height), case.bg)
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(case.lines):
        _draw_line(draw, (case.padding, case.padding + index * line_height), line, font,
                   fallback, case.fg)
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
