# TextJ

Ultra-fast local OCR utility for extracting text from images and screenshots.

TextJ is designed around one rule:

> **Capture -> OCR -> Clipboard should feel instant.**

The project focuses on low latency, local processing, Korean/English text, and a minimal workflow rather than a heavy OCR desktop application.

## Project goals

- Extract text from screenshots and images with minimal delay.
- Run locally by default.
- Support Korean + English mixed text.
- Keep the OCR engine replaceable.
- Make region capture -> clipboard the primary UX.
- Measure end-to-end latency, not only model inference time.

## Planned workflow

```text
Hotkey
  -> select region
  -> capture
  -> preprocess
  -> text detection
  -> recognition
  -> postprocess
  -> clipboard
```

## Documentation

- [Docs index](docs/README.md)
- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [OCR engine strategy](docs/OCR_ENGINE.md)
- [Performance targets](docs/PERFORMANCE.md)
- [Roadmap](docs/ROADMAP.md)

## Status

**Phase: project bootstrap / pre-v0.1**

The first milestone is a benchmarkable CLI OCR pipeline before tray UI or advanced capture features are added.
