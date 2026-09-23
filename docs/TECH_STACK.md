# Technology Stack

> Status: proposed stack for the first implementation. Every performance-sensitive choice remains benchmark-driven.

## 1. Core implementation strategy

TextJ should start with a **Python-first prototype** so OCR backends and preprocessing ideas can be tested quickly.

The project should not assume Python is the permanent implementation language.

Recommended evolution:

```text
v0.x
Python orchestration
+ native OCR runtimes
+ Windows API bindings

        ↓ profile

v1.x
keep Python where overhead is negligible
move hot paths to native code only when measured

        ↓ if required

future native core
C++/Rust shell
+ ONNX Runtime / Windows ML
+ native capture
```

The rule is simple: **rewrite only measured bottlenecks.**

---

## 2. OCR model candidates

### Primary baseline: PP-OCRv5 mobile

Current first candidate:

- lightweight text detector
- Korean recognition model
- Korean + English recognition support
- suitable for local inference
- available through multiple inference runtimes

Recommended baseline experiment:

```text
PP-OCR detector
+
korean_PP-OCRv5_mobile_rec
```

Why start here:

- Korean support is first-class enough for the target use case
- mobile recognizer is more suitable for latency work than large server models
- mature ecosystem
- easy to establish a baseline before custom optimization

### Integration candidate: RapidOCR

RapidOCR is useful as an early adapter because it exposes PP-OCR-family models through runtimes including ONNX Runtime and other backends.

TextJ should still wrap it behind its own interfaces:

```text
TextJ
  |
  +-- RapidOCRBackend
  |
  +-- NativeOnnxBackend
  |
  +-- FutureCustomBackend
```

RapidOCR should be treated as an implementation backend, not as TextJ architecture.

---

## 3. Inference runtime candidates

### ONNX Runtime CPU

**Role:** mandatory reference baseline.

Advantages:

- broad hardware compatibility
- simple deployment
- predictable comparison target
- provider abstraction
- mature profiling support

Every accelerated configuration should be compared against this baseline.

### Windows ML

**Role:** strong Windows-native deployment candidate.

Windows ML uses ONNX Runtime underneath and can select hardware execution providers for CPU, GPU, and NPU-class devices.

Possible benefits:

- Windows-oriented deployment
- future hardware provider flexibility
- hardware-specific provider discovery
- framework-dependent deployment option

TextJ should evaluate Windows ML after the basic ONNX Runtime pipeline is stable.

### CUDA Execution Provider

**Role:** NVIDIA-specific acceleration experiment.

Use only if:

```text
capture
+ transfer
+ inference
+ synchronization
< CPU total latency
```

A GPU benchmark that reports only model inference is insufficient.

### TensorRT / TensorRT RTX

**Role:** later NVIDIA optimization path.

Potential benefit:

- optimized graph execution
- reduced inference latency on supported NVIDIA hardware

Costs:

- packaging complexity
- engine compilation/cache management
- hardware/version-specific behavior

Not required for early TextJ versions.

### DirectML

DirectML remains useful as a broad DirectX 12 GPU path, but new Windows-side work should also evaluate the newer Windows ML execution-provider architecture.

It is an experiment target rather than the only Windows acceleration strategy.

---

## 4. Image processing

Initial recommendation:

- NumPy for image buffers
- OpenCV only for operations that provide measured value
- Pillow only where convenient for file format handling

Avoid automatically chaining many OpenCV filters.

A fast screenshot usually needs less processing than a photographed document.

Fast path:

```text
BGRA/RGBA input
-> channel normalization if required
-> detector resize
-> inference
```

Difficult-image path can selectively add:

- grayscale
- contrast normalization
- thresholding
- denoise
- deskew
- orientation correction

---

## 5. Windows integration

Preferred native primitives to investigate:

| Function | Candidate |
| --- | --- |
| global shortcut | Win32 RegisterHotKey |
| clipboard text | Win32 Clipboard API / CF_UNICODETEXT |
| region overlay | lightweight borderless transparent window |
| screen capture | DXGI Desktop Duplication / Windows.Graphics.Capture |
| process lifecycle | tray resident process |
| notifications | native toast or minimal tray feedback |

The main OCR action must not require opening a full GUI.

---

## 6. CLI

The CLI is the first stable frontend because it is easy to benchmark.

Planned commands:

```bash
textj image.png
textj image.png --json
textj image.png --mode fast
textj image.png --mode accurate
textj bench benchmarks/ui/
textj info
```

Possible `textj info` output:

```text
TextJ 0.x
backend: onnx
detector: ppocr
recognizer: ppocrv5-korean-mobile
provider: CPUExecutionProvider
device: CPU
warm: yes
```

---

## 7. Configuration

Suggested format:

```toml
mode = "fast"

[ocr]
backend = "onnx"
language = "ko-en"

[detector]
max_side = 960
threshold = 0.30

[recognizer]
batch_size = 8

[runtime]
provider = "auto"
warmup = true

[capture]
hotkey = "ctrl+shift+x"
```

Performance-critical defaults should be versioned.

---

## 8. Packaging candidates

Early development:

- normal Python virtual environment

Prototype executable:

- PyInstaller or Nuitka experiment

Long-term Windows build:

- benchmark startup size/time before choosing
- consider native shell if resident Python process becomes a deployment burden

Because TextJ is resident, executable cold-start time matters less than applications that restart for every OCR request.

---

## 9. Initial recommended stack

For the first working build:

```text
Python
  |
  +-- RapidOCR or direct PP-OCR adapter
  +-- ONNX Runtime CPU baseline
  +-- NumPy
  +-- minimal OpenCV
  +-- Win32 capture/clipboard bindings
```

Then benchmark:

```text
CPU ORT
vs
Windows ML / GPU
vs
CUDA
vs
other provider
```

The fastest reliable end-to-end path wins.
