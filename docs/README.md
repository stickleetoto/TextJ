# TextJ Documentation

This directory defines the technical direction of TextJ.

## Core idea

TextJ is not initially an OCR research project.

The first objective is to build an **extremely fast local OCR utility** using replaceable OCR backends and an aggressively optimized end-to-end pipeline.

The main metric is:

```text
user action -> usable text in clipboard
```

not only:

```text
model inference time
```

## Documents

### Product and roadmap

| Document | Purpose |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | Product scope, principles, use cases, non-goals |
| [ROADMAP.md](ROADMAP.md) | Development plan from v0.1 to v1.0 |

### Architecture and implementation

| Document | Purpose |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime architecture and module boundaries |
| [TECH_STACK.md](TECH_STACK.md) | Candidate languages, runtimes, APIs, packaging and first implementation stack |
| [WINDOWS_RUNTIME.md](WINDOWS_RUNTIME.md) | Hotkey, capture, clipboard, DPI, resident process and Windows-specific design |
| [CLIPBOARD.md](CLIPBOARD.md) | Current in-memory clipboard-image OCR implementation and limitations |
| [OCR_ENGINE.md](OCR_ENGINE.md) | OCR backend abstraction and recognition strategy |

### Performance engineering

| Document | Purpose |
| --- | --- |
| [PERFORMANCE.md](PERFORMANCE.md) | Performance goals, p50/p95 rules and latency budget |
| [OPTIMIZATION.md](OPTIMIZATION.md) | Pixel reduction, batching, warm-up, cache, quantization and copy reduction |
| [BENCHMARK_MATRIX.md](BENCHMARK_MATRIX.md) | Workload matrix, metrics, JSON results and regression gates |
| [TECH_RADAR.md](TECH_RADAR.md) | Adopt / Trial / Assess / Hold technology decisions |

## Initial technical baseline

Current first candidate stack:

```text
Windows-first
  |
  +-- Python prototype
  +-- PP-OCRv5 Korean mobile
  +-- RapidOCR and/or direct ONNX adapter
  +-- ONNX Runtime CPU baseline
  +-- NumPy
  +-- minimal OpenCV
  +-- native Windows hotkey/capture/clipboard path
```

The backend is intentionally replaceable.

## Performance doctrine

TextJ measures:

```text
trigger
+ capture
+ conversion
+ detection
+ crop
+ recognition
+ layout
+ clipboard
= total latency
```

Every performance-sensitive change should report both latency and OCR quality.

## Design rule

Every feature should answer one question:

> Does this make text extraction faster, more reliable, or easier to trigger?

If the answer is no, it is probably not a v1 feature.
