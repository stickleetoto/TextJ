# TextJ Documentation

This directory defines the initial technical direction of TextJ.

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

| Document | Purpose |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | Product scope, principles, use cases, non-goals |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime architecture and module boundaries |
| [OCR_ENGINE.md](OCR_ENGINE.md) | OCR backend strategy and optimization layers |
| [PERFORMANCE.md](PERFORMANCE.md) | Benchmark rules and latency targets |
| [ROADMAP.md](ROADMAP.md) | Development plan from v0.1 to v1.0 |

## Initial priorities

1. Build one reliable OCR pipeline.
2. Keep models warm in memory.
3. Benchmark every stage.
4. Add screen-region capture.
5. Copy recognized text immediately.
6. Optimize Korean + English mixed text.
7. Add optional GPU acceleration only where it actually improves end-to-end latency.

## Design rule

Every feature should answer one question:

> Does this make text extraction faster, more reliable, or easier to trigger?

If the answer is no, it is probably not a v1 feature.
