# Development Status

Last updated: 2026-09-23

## Current milestone

**v0.1 — OCR Core**

Status: **implementation started**

## Implemented

- Python package layout
- `textj` console entry point
- backend abstraction
- RapidOCR backend
- PP-OCRv5 mobile configuration
- Korean recognition model selection
- ONNX Runtime CPU baseline
- backend-independent `OCRLine` / `OCRResult`
- plain-text CLI output
- JSON output
- confidence threshold option
- end-to-end timing
- RapidOCR internal detector/classifier/recognizer timing export when available
- basic result model tests

## Current command

```bash
textj image.png --timing
```

Structured output:

```bash
textj image.png --json
```

## Installation

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -e ".[dev]"
```

RapidOCR may need to download the selected language model on the first run.
Subsequent OCR should use the local cached model files.

## Next work

### v0.1 completion

- run first real Korean screenshot benchmark
- validate model download/cache behavior on Windows
- record cold vs warm latency
- add more backend-independent tests
- add a tiny benchmark CLI
- create a small Korean/English fixture set

### then v0.2

Build the reproducible benchmark harness before doing serious performance tuning.

## Known limitations

- file input only
- no clipboard input yet
- no screen-region capture yet
- no resident process yet
- each CLI invocation is a new Python process
- first invocation can include model acquisition/loading cost
- line ordering currently follows backend output
- orientation classifier is intentionally disabled in the fast baseline
