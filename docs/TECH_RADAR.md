# Technology Radar

This is a living list of technologies considered for TextJ.

Last reviewed: 2026-09-23

## ADOPT

### ONNX Runtime CPU baseline

Use as the first reproducible inference baseline.

Reason:

- mature
- local
- portable
- provider abstraction
- straightforward profiling

### PP-OCRv5 Korean mobile recognizer

Use as the first Korean/English recognition candidate.

Reason:

- purpose-built Korean model
- English included in Korean multilingual recognition support
- mobile model fits TextJ latency goals

### Warm resident runtime

Architectural requirement for desktop mode.

### Stage-level timing

Architectural requirement from v0.1.

---

## TRIAL

### RapidOCR

Use to accelerate first integration and compare against a more direct model/runtime adapter.

### Windows ML

Evaluate as a Windows-native inference deployment/provider layer after the CPU baseline is stable.

### CUDA Execution Provider

Evaluate on NVIDIA systems.

### DXGI Desktop Duplication

Strong candidate for low-latency monitor capture and future dirty-region OCR.

### Windows.Graphics.Capture

Benchmark for modern Windows window/display capture workflows.

### Quantized OCR models

Evaluate INT8/FP16 only with accuracy and end-to-end latency measurements.

---

## ASSESS

### TensorRT / TensorRT RTX

Potential NVIDIA-specific optimization after the standard GPU path is established.

### OpenVINO

Worth testing on Intel-heavy CPU/iGPU hardware if distribution needs justify it.

### Rust/C++ native core

Consider only after profiling demonstrates orchestration/copy overhead that cannot be fixed cleanly in the prototype.

### OCR crop cache

Potential major win for repeated on-screen content.

### Dirty-region OCR

Useful for future live/watch modes.

### NPU execution providers

Potential future path as Windows hardware/provider availability becomes common enough to justify support.

---

## HOLD

### Training a custom OCR model before v1

Do not begin here.

First establish:

- real dataset
- reproducible benchmark
- backend baseline
- latency bottlenecks
- failure examples

Then custom model work has a measurable target.

### Heavy Electron-style desktop shell

TextJ should not spend hundreds of MB of runtime overhead for a tray utility without a compelling reason.

### Cloud OCR as default

Conflicts with:

- local-first goal
- latency predictability
- offline support
- screenshot privacy

Cloud OCR can only be an explicit optional backend in a later version, if ever.

### Mandatory image enhancement pipeline

Many screenshots are already clean.

Preprocessing should be triggered by evidence, not applied blindly.
