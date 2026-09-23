# TextJ

Ultra-fast local OCR utility for extracting text from images and screenshots.

TextJ is designed around one rule:

> **Capture -> OCR -> Clipboard should feel instant.**

The project focuses on low latency, local processing, Korean/English text, and a minimal workflow rather than a heavy OCR desktop application.

## Status

**v0.1 OCR Core — implementation started**

The current build accepts an image file, runs local OCR through a replaceable backend, and emits plain text or structured JSON.

## Current stack

```text
TextJ CLI
   |
   v
OCRPipeline
   |
   v
RapidOCR adapter
   |
   +-- PP-OCRv5 mobile detector
   +-- PP-OCRv5 Korean mobile recognizer
   |
   v
ONNX Runtime CPU
```

The backend boundary is intentional: RapidOCR is the first baseline, not a permanent architectural dependency.

## Install

Python 3.10+ is required.

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -e ".[dev]"
```

## Use

```bash
textj screenshot.png
```

Show timing:

```bash
textj screenshot.png --timing
```

Structured output:

```bash
textj screenshot.png --json
```

English recognition model:

```bash
textj screenshot.png --language en
```

Korean is the default recognition model.

> The first OCR run may include model download/loading work. TextJ measures warm steady-state performance separately as the resident runtime is introduced.

## v1 target workflow

```text
global hotkey
  -> select screen region
  -> capture
  -> detect text
  -> recognize
  -> clipboard
```

## Project goals

- Extract text from screenshots and images with minimal delay.
- Run locally by default.
- Support Korean + English mixed text.
- Keep the OCR engine replaceable.
- Make region capture -> clipboard the primary UX.
- Measure end-to-end latency, not only model inference time.

## Documentation

- [Docs index](docs/README.md)
- [Current development status](docs/STATUS.md)
- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Technology stack](docs/TECH_STACK.md)
- [OCR engine strategy](docs/OCR_ENGINE.md)
- [Optimization strategy](docs/OPTIMIZATION.md)
- [Windows runtime](docs/WINDOWS_RUNTIME.md)
- [Performance targets](docs/PERFORMANCE.md)
- [Benchmark matrix](docs/BENCHMARK_MATRIX.md)
- [Technology radar](docs/TECH_RADAR.md)
- [Roadmap](docs/ROADMAP.md)

## License

MIT
