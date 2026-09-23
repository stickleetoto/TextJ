# Claude Handoff — TextJ

Last prepared: 2026-09-24

## Mission

TextJ should become a **very fast local Windows OCR utility**.

The intended final interaction is:

```text
global hotkey
-> drag a rectangle over visible text
-> release mouse
-> OCR runs locally
-> recognized text is placed in clipboard
```

The interaction should feel closer to a native OS shortcut than opening an OCR application.

---

## Repository state at handoff

Baseline commit before this handoff:

`6bcf98f7f4593c291ff1c02f0c7b4ccad5ca26a1`

Implemented before handoff:

### OCR core

- Python package
- backend abstraction
- RapidOCR adapter
- PP-OCRv5 mobile detector
- PP-OCRv5 Korean mobile recognizer
- ONNX Runtime CPU baseline
- file input
- NumPy in-memory input
- OCR result model
- text, scores and boxes
- JSON output
- internal timing export where available

### Benchmarking

- `textj-bench`
- warmups + repeated runs
- min / mean / p50 / p95 / max
- sampled RSS
- optional ground-truth CER
- JSON result output
- system/runtime metadata
- benchmark manifest format
- `textj-bench-suite`

### Clipboard prototype

- read clipboard image using Pillow
- convert image directly to contiguous BGR ndarray
- OCR without a temporary image file
- write recognized text through Win32 `CF_UNICODETEXT`
- `textj-clipboard`
- `--no-copy`, `--json`, `--timing`

---

## Important caveat

The code has not yet been field-validated on the target Windows machine after the most recent changes.

Do **not** assume that all current code paths are bug-free just because they are present.

The first job is to run tests and inspect failures.

---

## First commands

From a fresh clone/update:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
```

Then inspect commands:

```powershell
textj --help
textj-bench --help
textj-bench-suite --help
textj-clipboard --help
```

With a real screenshot:

```powershell
textj screenshot.png --timing
textj-bench screenshot.png --runs 20 --warmups 2
```

With an image copied to the Windows clipboard:

```powershell
textj-clipboard --timing
```

---

## Likely first issues to inspect

### 1. RapidOCR ndarray path

Confirm that the current RapidOCR version accepts TextJ's BGR ndarray path exactly as expected.

Do not add disk fallback unless necessary.

### 2. Clipboard ownership and locking

Win32 clipboard operations can fail temporarily if another process has it open.

The current implementation may need bounded retry/backoff.

Never create an infinite retry.

### 3. CLI model construction cost

Every current CLI command creates a new OCR backend.

This is expected for now but is unacceptable for the final UX.

The resident runtime is the highest-value architectural next step.

### 4. Benchmark interpretation

Current sampled RSS is not a true continuously measured peak.

Label it accurately unless a real peak sampler is added.

### 5. OCR line ordering

Backend output ordering may not always match visual reading order.

Do not attempt elaborate layout analysis before collecting failure examples.

---

## Architectural direction

Target architecture:

```text
                   +----------------------+
global hotkey ---->| resident TextJ host  |
                   |                      |
region selector -->| capture adapter      |
                   |        |             |
                   |        v             |
clipboard image -->| in-memory image      |
                   |        |             |
                   |        v             |
                   | warm OCR pipeline    |
                   |        |             |
                   |        v             |
                   | postprocess          |
                   |        |             |
                   |        v             |
                   | Win32 clipboard      |
                   +----------------------+
```

Do not launch Python + model initialization for every OCR action.

---

## Performance targets

These are targets, not claimed achievements.

### Small region

- v1 target: <= 250 ms warm
- stretch: <= 150 ms

### Ordinary screen region

- v1 target: <= 500 ms warm
- stretch: <= 300 ms

### Dense document-like image

- target: <= 1 second warm when the selected backend permits it

p95 matters more than one lucky run.

---

## Accuracy policy

The default fast path must not chase maximum benchmark accuracy at any cost.

Preferred model:

```text
fast path
   |
   +-- confident -> output
   |
   +-- low confidence -> targeted accurate retry
```

Keep code/terminal text preservation in mind.

---

## Development strategy

### Build product infrastructure before model research

The preferred order is:

```text
working OCR
-> reproducible benchmark
-> resident runtime
-> capture UX
-> measured optimization
-> quality regression suite
-> packaging
-> only then custom-model research
```

### Profile before rewriting

A Rust/C++ rewrite is allowed later if profiling shows Python orchestration is a real bottleneck.

Do not rewrite preemptively.

---

## Relevant documents

- `docs/STATUS.md` — current factual state
- `docs/ROADMAP.md` — version roadmap
- `docs/EXECUTION_PLAN.md` — active task queue
- `docs/ARCHITECTURE.md` — module boundaries
- `docs/PERFORMANCE.md` — measurement policy
- `docs/BENCHMARK_MATRIX.md` — benchmark dimensions
- `docs/OPTIMIZATION.md` — optimization ideas
- `docs/WINDOWS_RUNTIME.md` — Windows design
- `docs/CLIPBOARD.md` — clipboard path
- `docs/TECH_RADAR.md` — adopted/trial technologies
- `docs/DEV_WORKLOG.md` — chronological development log

---

## Desired agent behavior

Be implementation-heavy.

If the current milestone can be moved forward safely, move it forward instead of only suggesting it.

When finishing one task:

1. test it,
2. update status/worklog,
3. start the next unblocked task.

Stop only at a meaningful checkpoint, a hard blocker, or when further work would require unavailable hardware/user action.
