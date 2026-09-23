# Benchmark Matrix

## 1. Why this exists

TextJ should choose technology using reproducible measurements.

The benchmark matrix prevents conclusions such as:

> GPU is faster.

without asking:

> On which image size, model, provider, hardware, batch size, and metric?

---

## 2. Workload classes

### S — tiny selection

Examples:

- one error message
- one UI label group
- 1–3 text lines

Typical size:

```text
~200x50 to ~800x250
```

### M — normal region

Examples:

- chat message group
- code excerpt
- article paragraph

Typical size:

```text
~600x300 to ~1600x900
```

### L — full screen

Examples:

- 1920x1080 application screenshot
- dense webpage
- IDE

### XL — high resolution

Examples:

- 2560x1440
- 3840x2160

---

## 3. Content classes

Each workload size should include several content types.

| ID | Content |
| --- | --- |
| KO | Korean prose |
| EN | English prose |
| MIX | Korean + English |
| CODE | code and identifiers |
| TERM | terminal output |
| UI | application UI |
| DARK | dark theme |
| TINY | small fonts |
| HARD | low contrast/compressed |

---

## 4. Backend matrix

Initial candidates:

| Backend | Runtime/provider | Purpose |
| --- | --- | --- |
| PP-OCRv5 Korean mobile | ONNX Runtime CPU | baseline |
| PP-OCRv5 Korean mobile | Windows acceleration candidate | experiment |
| PP-OCRv5 Korean mobile | CUDA | NVIDIA experiment |
| RapidOCR pipeline | ONNX Runtime | integration speed/baseline |
| future custom adapter | varies | later |

The exact same source images and ground truth must be used across candidates.

---

## 5. Variables to sweep

### Detector

- longest-side resize
- threshold
- box threshold
- unclip/expansion ratio where applicable

### Recognizer

- input height
- maximum width
- batch size
- model precision

### Runtime

- provider
- thread count
- optimization level
- memory arena settings if relevant

### Pipeline

- preprocessing on/off
- detector bypass on/off
- box merge strategy
- confidence retry threshold

---

## 6. Metrics

### Latency

- cold start
- cold first OCR
- warm p50
- warm p95
- warm p99 when run count is large enough
- stage timings

### Accuracy

- character error rate
- word/line exact match
- detection recall
- detection precision when box ground truth exists

### Resource

- idle RSS
- peak RSS
- GPU VRAM
- CPU utilization
- package/model size

---

## 7. Benchmark result schema

Suggested JSON:

```json
{
  "textj_version": "0.2.0",
  "timestamp": "ISO-8601",
  "system": {
    "os": "Windows",
    "cpu": "...",
    "gpu": "...",
    "ram_gb": 0
  },
  "ocr": {
    "detector": "...",
    "recognizer": "...",
    "provider": "...",
    "precision": "fp32"
  },
  "config": {
    "detector_max_side": 960,
    "batch_size": 8
  },
  "result": {
    "warm_p50_ms": 0,
    "warm_p95_ms": 0,
    "cer": 0.0,
    "rss_mb": 0
  }
}
```

---

## 8. Regression gates

An optimization can be automatically rejected if it violates configured limits.

Example:

```text
latency improves 12%
BUT
CER worsens > 2 percentage points

=> reject for default fast mode
```

Different gates can exist for:

- fast mode
- accurate mode

---

## 9. Pareto frontier

Do not select configurations with one scalar score too early.

Plot or compare:

```text
latency <-> accuracy
memory  <-> latency
size    <-> accuracy
```

Keep configurations that are non-dominated.

This can naturally produce:

- Fast preset
- Balanced preset
- Accurate preset

---

## 10. Reference hardware tiers

Eventually report at least:

### CPU-only baseline

A common laptop/desktop CPU.

### Integrated/commodity GPU

Useful for Windows-wide acceleration experiments.

### NVIDIA GPU

CUDA/TensorRT comparison.

The benchmark harness should not assume one developer machine is representative of every TextJ installation.
