# Architecture

## 1. Overview

TextJ is designed as a latency-oriented pipeline.

```text
Trigger
  |
  v
Capture / Input
  |
  v
Image normalization
  |
  v
Text detection
  |
  +--------------------+
  | candidate regions  |
  v                    |
Region preparation     |
  |                    |
  v                    |
Text recognition <-----+
  |
  v
Postprocessing
  |
  v
Clipboard / stdout / file
```

The desktop process should remain alive so model initialization is not repeated for each capture.

---

## 2. Proposed repository structure

```text
TextJ/
├─ src/
│  └─ textj/
│     ├─ app/
│     │  ├─ cli.py
│     │  ├─ tray.py
│     │  └─ hotkey.py
│     ├─ capture/
│     │  ├─ screen.py
│     │  ├─ clipboard.py
│     │  └─ files.py
│     ├─ image/
│     │  ├─ normalize.py
│     │  ├─ resize.py
│     │  └─ orientation.py
│     ├─ detection/
│     │  ├─ base.py
│     │  └─ backends/
│     ├─ recognition/
│     │  ├─ base.py
│     │  └─ backends/
│     ├─ pipeline/
│     │  ├─ fast.py
│     │  ├─ accurate.py
│     │  └─ result.py
│     ├─ postprocess/
│     │  ├─ layout.py
│     │  └─ cleanup.py
│     ├─ output/
│     │  ├─ clipboard.py
│     │  └─ console.py
│     ├─ runtime/
│     │  ├─ models.py
│     │  ├─ session.py
│     │  └─ device.py
│     └─ metrics/
│        └─ timing.py
├─ benchmarks/
├─ tests/
├─ models/
├─ scripts/
└─ docs/
```

The exact names can change, but the boundaries should remain clear.

---

## 3. Core interfaces

### Detector

Input:

- normalized image

Output:

- text region polygons or boxes
- optional detection confidence

Conceptual interface:

```python
class TextDetector:
    def detect(self, image) -> list[TextRegion]:
        ...
```

### Recognizer

Input:

- cropped text region

Output:

- text
- confidence
- optional language metadata

```python
class TextRecognizer:
    def recognize(self, crop) -> Recognition:
        ...
```

### OCR pipeline

The pipeline owns ordering and optimization decisions.

```python
class OCRPipeline:
    def run(self, image) -> OCRResult:
        ...
```

This allows detection and recognition engines to be swapped independently.

---

## 4. Runtime lifecycle

### Cold path

```text
process start
-> load configuration
-> initialize runtime
-> load OCR models
-> warm-up inference
-> ready
```

### Warm path

```text
trigger
-> acquire image
-> run OCR pipeline
-> postprocess
-> write clipboard
```

The warm path is the primary optimization target.

---

## 5. Fast path strategy

A common mistake is sending the original full-resolution screenshot directly through every OCR stage.

TextJ should instead use a staged path.

```text
original image
  |
  +-> reduced detector image
          |
          v
     find text areas
          |
          v
crop corresponding regions from original image
          |
          v
recognize only useful pixels
```

This makes detector cost depend on a bounded input size while preserving text detail during recognition.

---

## 6. Region scheduling

Detected regions should normally be:

1. filtered,
2. ordered,
3. batched where supported,
4. recognized,
5. reassembled into reading order.

Tiny regions below a configurable threshold may be dropped in fast mode.

Duplicate or strongly overlapping boxes should be merged before recognition.

---

## 7. Threading and concurrency

Concurrency is useful only when it lowers total latency.

Potential parallel work:

- capture and runtime readiness checks,
- preprocessing independent crops,
- batched recognition,
- output formatting after recognition.

Avoid spawning a new worker process for each OCR action.

Long-lived threads or runtime sessions are preferred.

---

## 8. Memory policy

The desktop service may intentionally trade some memory for speed.

Preferred:

- keep model sessions alive,
- keep reusable buffers when practical,
- avoid repeatedly loading model weights,
- avoid unnecessary image copies,
- reuse preallocated arrays when profiling shows benefit.

Memory optimization comes after eliminating major latency sources.

---

## 9. Platform direction

### Initial platform

Windows-first desktop workflow.

Reasons:

- primary intended environment,
- global hotkey and region capture are central features,
- the first benchmark target can remain controlled.

### Later

The core OCR pipeline should remain platform-independent enough to support Linux and possibly macOS later.

Platform-specific code should stay inside capture, hotkey, tray, and clipboard adapters.

---

## 10. Failure behavior

A failed OCR attempt should fail quickly and visibly.

Examples:

- empty selection -> no OCR
- no text detected -> short notification, clipboard unchanged by default
- backend unavailable -> clear fallback or error
- GPU provider failure -> retry on CPU if configured
- unsupported image -> explicit error

Silent multi-second fallback chains should be avoided.

---

## 11. Observability

Every pipeline run should optionally expose stage timing:

```text
capture          8 ms
normalize        3 ms
detect          42 ms
crop             2 ms
recognize        71 ms
postprocess      2 ms
clipboard        1 ms
----------------------
total          129 ms
```

Performance work without stage-level timing is not accepted as optimization.
