# TextJ Execution Plan

This is the active engineering queue.

The version roadmap describes product milestones. This file describes the **recommended execution order** for an autonomous development session.

Use checkboxes honestly. Do not mark tasks done without implementation and validation appropriate to the task.

---

# Phase A — Stabilize Current Core

## A1. Clean environment validation

- [ ] install from `pip install -e ".[dev]"`
- [ ] run full `pytest -q`
- [ ] fix packaging/import/type failures
- [ ] ensure all four console scripts start
- [ ] verify unit tests do not require model download

### Exit

A clean developer environment can install TextJ and run tests.

---

## A2. Real OCR smoke

- [ ] Korean screenshot
- [ ] English screenshot
- [ ] mixed Korean/English screenshot
- [ ] code or terminal screenshot
- [ ] dark-theme screenshot
- [ ] record backend initialization latency
- [ ] record first inference latency
- [ ] record warm p50/p95
- [ ] record failure examples, not only successes

### Exit

There is at least one real baseline result and known failure set.

---

## A3. Clipboard hardening

- [ ] validate Pillow clipboard path on Windows
- [ ] validate ndarray channel ordering against RapidOCR
- [ ] add bounded retry for Win32 clipboard locking if needed
- [ ] do not overwrite clipboard on empty OCR
- [ ] preserve Unicode/newlines
- [ ] add platform guards
- [ ] add tests for error paths

### Exit

Clipboard-image -> OCR -> clipboard-text works reliably enough for manual use.

---

# Phase B — Finish Benchmark Foundation

## B1. Benchmark artifact quality

- [ ] include TextJ version/commit metadata when available
- [ ] include image dimensions
- [ ] include backend/model config
- [ ] distinguish cold backend construction from warm OCR
- [ ] validate CER normalization policy
- [ ] preserve raw per-run samples

## B2. Regression gates

Add a small command/module that compares two benchmark JSON files.

Report:

- p50 delta
- p95 delta
- CER delta
- RSS delta

Do not invent a single universal score.

- [ ] comparison implementation
- [ ] tests
- [ ] readable console output
- [ ] optional machine-readable JSON
- [ ] threshold-based nonzero exit code for CI/local automation

## B3. Fixture corpus

Create safe, purpose-built fixtures where practical.

Target categories:

- [ ] KO
- [ ] EN
- [ ] MIX
- [ ] CODE
- [ ] TERM
- [ ] UI
- [ ] DARK
- [ ] TINY

Avoid committing copyrighted or private screenshots casually.

### Phase B exit

TextJ can detect performance/accuracy regression instead of relying on subjective impressions.

---

# Phase C — Resident OCR Runtime

This phase has high priority because process/model initialization destroys interactive latency.

## C1. Runtime object

Create a long-lived service object that owns:

- OCR backend
- model/session lifecycle
- readiness state
- configuration
- execution serialization or queueing
- shutdown

Suggested conceptual API:

```python
runtime = TextJRuntime(config)
runtime.start()
result = runtime.ocr(image)
runtime.close()
```

- [ ] lifecycle
- [ ] warmup
- [ ] error states
- [ ] tests with fake backend
- [ ] timing hooks

## C2. Local IPC boundary

Choose the simplest reliable Windows-local mechanism.

Candidates:

- named pipe
- localhost socket
- other lightweight local IPC

Requirements:

- local-only
- bounded requests
- explicit protocol version
- no arbitrary code execution
- text/metadata messages should be simple
- avoid encoding image to PNG when shared/raw memory path is practical later

Start simple. Optimize transport only after measuring.

- [ ] protocol
- [ ] server
- [ ] client
- [ ] health/readiness
- [ ] graceful shutdown
- [ ] malformed-request handling

## C3. Clipboard command through resident runtime

- [ ] reuse already-loaded OCR backend
- [ ] measure before/after
- [ ] preserve standalone fallback only if useful

### Phase C exit

Repeated clipboard OCR no longer pays model construction on every action.

---

# Phase D — Windows Hotkey and Region Capture

## D1. Global hotkey

Baseline candidate:

Win32 `RegisterHotKey`

- [ ] configurable hotkey
- [ ] conflict handling
- [ ] no unnecessary low-level keyboard hook
- [ ] clean unregister on exit

## D2. Region selector

Requirements:

- [ ] borderless lightweight overlay
- [ ] drag rectangle
- [ ] Escape cancel
- [ ] multi-monitor coordinates
- [ ] negative monitor coordinates
- [ ] DPI awareness
- [ ] minimum selection size
- [ ] close overlay immediately on release

Keep UI minimal.

## D3. Capture backend

Benchmark:

- Windows.Graphics.Capture
- DXGI/Desktop Duplication where practical

Measure request-to-usable-pixels, not FPS.

- [ ] 1080p
- [ ] 1440p if available
- [ ] 4K if available
- [ ] crop extraction cost
- [ ] pixel conversion cost

## D4. Direct path

Target:

```text
hotkey
-> region
-> captured memory
-> OCR
-> clipboard
```

No temporary files.

### Phase D exit

TextJ's north-star workflow is functional.

---

# Phase E — Fast Pipeline Optimization

Do not guess. Use Phase B measurements.

## E1. Detector resolution sweep

Test bounded longest-side sizes such as:

- 640
- 768
- 960
- 1280

Measure latency and detection/recognition quality.

## E2. Workload classes

Implement only if benchmark evidence supports them.

Potential classes:

```text
S = small/single-line
M = ordinary region
L = large/dense
X = difficult/low confidence
```

## E3. Single-line detector bypass

Experiment only.

- [ ] cheap layout heuristic
- [ ] benchmark
- [ ] accuracy guard
- [ ] fallback on uncertainty

## E4. Crop/box improvements

- [ ] overlap suppression
- [ ] duplicate removal
- [ ] tiny-noise filtering
- [ ] reading-order reconstruction
- [ ] crop-size bucketing
- [ ] recognition batching if backend allows useful control

## E5. Quantization/provider experiments

Candidates:

- CPU FP32 baseline
- INT8 where supported
- FP16 on suitable provider
- CUDA provider
- Windows ML/provider path
- TensorRT later

Measure total latency.

### Phase E exit

Default fast mode has evidence-based configuration rather than arbitrary tuning.

---

# Phase F — Quality and Adaptive OCR

## F1. Failure corpus

Keep examples of:

- Korean + English mixing
- terminal output
- code
- URLs
- filenames
- punctuation
- tiny fonts
- dark UI
- low contrast

## F2. Targeted fallback

Prototype:

```text
fast OCR
-> confidence/heuristic check
-> only difficult regions retry
```

- [ ] no full-image double OCR unless justified
- [ ] preserve fast common case

## F3. Reading order

Improve only against concrete fixtures.

### Phase F exit

Quality improvements are regression-tested and do not silently destroy the fast path.

---

# Phase G — Desktop Reliability and Packaging

## G1. Tray host

- [ ] runtime status
- [ ] enable/disable hotkey
- [ ] exit
- [ ] minimal settings access

## G2. Configuration

Versioned TOML or similarly simple local config.

Include:

- hotkey
- language
- fast/accurate mode
- provider
- thresholds

## G3. Packaging

Evaluate:

- PyInstaller
- Nuitka
- native host only if needed

Measure:

- package size
- cold startup
- idle RSS
- update friction

## G4. Failure recovery

- [ ] OCR backend failure
- [ ] clipboard unavailable
- [ ] capture device reset
- [ ] malformed config
- [ ] resident runtime restart

### Phase G exit

A normal Windows user can install and use TextJ without a Python development environment.

---

# Phase H — After v1

Only after the core product is good:

- additional languages
- optional history
- Linux port
- layout-preserving output
- continuous/watch OCR
- dirty-region OCR
- NPU providers
- custom distilled/screen-text recognition model

Do not pull these forward unless they directly unblock v1.
