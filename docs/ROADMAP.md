# Roadmap

## North star

```text
Hotkey -> drag -> release -> text in clipboard
```

The roadmap deliberately builds the measurable OCR core before the desktop UX.

---

# v0.1 — OCR Core

**Status: core implementation present; real-device validation pending.**

Goal: prove that TextJ can recognize Korean/English text from an image through a clean internal API.

### Deliverables

- project package structure
- CLI entry point
- image file input
- one OCR backend adapter
- Korean + English recognition
- structured OCR result
- plain-text stdout output
- basic unit tests
- stage timing instrumentation

### Example

```bash
textj image.png
```

Output:

```text
recognized text...
```

### Exit criteria

- one image can be processed reliably,
- model/session is reusable,
- stage timings are visible,
- OCR engine code is isolated behind an adapter.

---

# v0.2 — Benchmark Foundation

**Status: IN PROGRESS — runner, p50/p95, RSS sampling, CER, JSON persistence, manifests and suite runner implemented.**

Goal: make performance measurable before optimization begins.

### Deliverables

- `benchmarks/` dataset layout
- benchmark runner
- p50/p95 reporting
- cold vs warm separation
- per-stage timing
- memory measurement
- expected-text fixtures
- CER calculation
- benchmark result JSON

### Exit criteria

Every optimization can answer:

> Did it actually make TextJ faster, and what accuracy did it cost?

---

# v0.3 — Fast Pipeline

Goal: reduce work before recognition.

### Deliverables

- detector-resolution cap
- coordinate mapping to original image
- original-resolution text crops
- minimum box filtering
- overlapping box merge
- reading-order reconstruction
- recognition batching
- fast-mode configuration

### Exit criteria

- full image is not blindly sent through expensive recognition,
- benchmark improvement is demonstrated,
- accuracy regression is documented.

---

# v0.4 — Clipboard Image OCR

**Status: early prototype implemented ahead of schedule — in-memory image input and Win32 text copy work are present; resident-runtime integration remains.**

Goal: remove file-save friction.

### Deliverables

- image read from clipboard
- OCR clipboard image
- copy recognized text back to clipboard
- configurable behavior when no text is found

### Target UX

```text
copy image
-> trigger TextJ
-> paste recognized text
```

---

# v0.5 — Screen Region Capture

Goal: implement the main TextJ interaction.

### Deliverables

- screen overlay
- click-drag region selection
- multi-monitor-safe coordinates
- Escape to cancel
- selected-region capture
- automatic OCR
- automatic clipboard output

### Exit criteria

No normal application window is required for the main workflow.

---

# v0.6 — Resident Runtime

Goal: remove repeated startup cost.

### Deliverables

- long-lived TextJ process
- model loaded once
- warm-up on startup
- global hotkey
- tray integration
- clean shutdown
- configuration file

### Main target

The normal OCR action uses the warm path.

---

# v0.7 — Korean/English Quality Pass

Goal: improve real screen-text usefulness.

### Deliverables

- mixed Korean/English benchmark set
- punctuation handling
- line ordering improvements
- code/terminal preservation rules
- URL/path preservation
- confidence reporting
- regression fixtures

### Avoid

Do not add aggressive spelling correction that damages code, identifiers, or filenames.

---

# v0.8 — Adaptive OCR

Goal: make easy images fast and difficult images recoverable.

### Deliverables

- fast mode
- accurate mode
- confidence threshold
- optional second-pass OCR
- difficult-image preprocessing hooks
- orientation handling where necessary

### Pipeline

```text
fast pass
  |
  +-- confident --> return
  |
  +-- uncertain --> targeted accurate pass
```

---

# v0.9 — Acceleration & Packaging

Goal: prepare a distributable build and tune supported hardware paths.

### Deliverables

- CPU baseline finalized
- optional accelerated inference provider
- provider auto-detection
- graceful CPU fallback
- packaged Windows application
- model/runtime packaging
- startup and memory profiling
- benchmark report for reference systems

### Important rule

GPU acceleration is kept only when it improves total latency enough to justify initialization and transfer overhead.

---

# v1.0 — TextJ

Goal: stable daily-use ultra-fast local OCR utility.

### Required features

- global region OCR hotkey
- clipboard image OCR
- file OCR
- Korean + English
- local processing
- warm resident runtime
- auto-copy result
- fast / accurate modes
- reproducible benchmark suite
- backend abstraction
- packaged Windows release

### v1 quality gates

- no model reload per OCR action
- no known blocking crash in normal region capture
- deterministic fallback behavior
- documented benchmark methodology
- acceptable p95 latency on reference hardware
- OCR quality regressions covered by fixtures

---

# After v1

Possible directions:

### v1.x

- batch folder OCR
- additional languages
- custom hotkeys
- lightweight history
- layout-preserving output
- CLI JSON output
- Linux support

### v2 research

- custom TextJ recognition model
- screen-text specialized dataset
- quantized/distilled recognizer
- tiny-text specialization
- model auto-selection by image type

A custom model becomes worthwhile only after the v1 benchmark system can prove that it is better than existing backends for TextJ's actual use cases.
