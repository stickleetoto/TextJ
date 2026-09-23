# TextJ

Ultra-fast local OCR utility for extracting text from images and screenshots.

TextJ is designed around one rule:

> **Capture -> OCR -> Clipboard should feel instant.**

The project focuses on low latency, local processing, Korean/English text, and a minimal workflow rather than a heavy OCR desktop application.

## Status

**v0.1 OCR Core implemented, v0.2 benchmark work in progress, clipboard OCR prototype available.**

The current build accepts either an image file or an in-memory clipboard image, runs local OCR through a replaceable backend, and can emit plain text, structured JSON, benchmark artifacts, or clipboard text.

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

Warm latency benchmark:

```bash
textj-bench screenshot.png --runs 20 --warmups 2
```

Machine-readable benchmark:

```bash
textj-bench screenshot.png --runs 20 --warmups 2 --json
```

Measure OCR accuracy against expected text and save the result:

```bash
textj-bench screenshot.png \
  --expected expected.txt \
  --runs 20 \
  --warmups 2 \
  --output benchmarks/results/sample.json
```

Run a multi-image regression suite:

```bash
textj-bench-suite benchmarks/manifest.json \
  --runs 10 \
  --warmups 1 \
  --output benchmarks/results/baseline.json
```

The benchmark output records p50/p95 latency, sampled RSS memory, OCR confidence, CER when ground truth exists, and system/runtime metadata.

Clipboard image OCR on Windows:

```powershell
textj-clipboard --timing
```

This reads the image directly from the clipboard into memory, runs OCR without writing a temporary image file, then replaces the clipboard with the recognized text.

Inspect without replacing the clipboard:

```powershell
textj-clipboard --no-copy
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

## Development handoff

For autonomous/agent development:

- [Claude instructions](CLAUDE.md)
- [Claude handoff](docs/HANDOFF_CLAUDE.md)
- [Execution plan](docs/EXECUTION_PLAN.md)
- [Definition of done](docs/DEFINITION_OF_DONE.md)
- [Development worklog](docs/DEV_WORKLOG.md)
- [Claude kickoff prompt](docs/CLAUDE_KICKOFF_PROMPT.md)

The handoff documents are intended to let a new development session continue from repository state without reconstructing the project from chat history.

## Documentation

- [Docs index](docs/README.md)
- [Current development status](docs/STATUS.md)
- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Technology stack](docs/TECH_STACK.md)
- [OCR engine strategy](docs/OCR_ENGINE.md)
- [Optimization strategy](docs/OPTIMIZATION.md)
- [Windows runtime](docs/WINDOWS_RUNTIME.md)
- [Clipboard OCR](docs/CLIPBOARD.md)
- [Performance targets](docs/PERFORMANCE.md)
- [Benchmark matrix](docs/BENCHMARK_MATRIX.md)
- [Technology radar](docs/TECH_RADAR.md)
- [Roadmap](docs/ROADMAP.md)

## License

MIT
