# TextJ — Claude Development Instructions

You are working on **TextJ**, an ultra-fast local OCR utility.

The product goal is simple:

> **Hotkey -> select text on screen -> release -> usable text is already in the clipboard.**

TextJ is not primarily an OCR-model research project. It is a **latency-focused desktop OCR product**. Reuse mature OCR models first, then optimize the whole path from user action to clipboard.

Read these before major work:

1. `docs/HANDOFF_CLAUDE.md`
2. `docs/STATUS.md`
3. `docs/ROADMAP.md`
4. `docs/ARCHITECTURE.md`
5. `docs/PERFORMANCE.md`
6. `docs/EXECUTION_PLAN.md`

---

## 1. Development mode

Work autonomously and keep moving.

Do not stop after producing plans when implementation is possible. Prefer:

```text
inspect
-> implement
-> test
-> benchmark where possible
-> document result
-> continue to the next unblocked task
```

If one task is blocked by platform/hardware/manual validation, record the blocker and move to the next independent task.

Do not wait for approval between ordinary implementation steps.

---

## 2. Non-negotiable product rules

### Latency first

Optimize **time-to-clipboard**, not isolated model inference.

The important measurement is:

```text
trigger
+ capture
+ conversion
+ detection
+ crop
+ recognition
+ postprocess
+ clipboard
= user-visible latency
```

### Local first

Default OCR must stay local and work offline after required models are available.

Do not introduce cloud OCR as a required dependency.

### Warm runtime

The final desktop path must not initialize the OCR model on every request.

A resident model/runtime is a core architectural requirement.

### Korean + English first

Mixed Korean/English screen text is the primary language target.

Do not damage code, URLs, paths, filenames, identifiers, or punctuation with aggressive language correction.

### Replaceable backend

RapidOCR is the first backend, not the architecture.

Keep OCR behind a backend interface.

---

## 3. Current stack

Baseline:

- Python 3.10+
- RapidOCR 3.x
- PP-OCRv5 mobile detector
- PP-OCRv5 Korean mobile recognizer
- ONNX Runtime CPU baseline
- NumPy
- Pillow
- psutil
- Win32 clipboard integration

Current CLI entry points:

```text
textj
textj-bench
textj-bench-suite
textj-clipboard
```

---

## 4. Engineering rules

### Preserve working paths

Do not rewrite the entire project because another architecture looks cleaner.

Refactor only when the current design materially blocks correctness, testing, or latency.

### Measure performance claims

Do not write "faster", "optimized", or "low latency" without measurements.

For performance-sensitive changes, prefer reporting:

- p50
- p95
- max
- CER or another accuracy metric when applicable
- RSS / memory impact
- configuration used

### Avoid unnecessary image copies

Never add a pipeline like:

```text
capture -> PNG encode -> disk -> PNG decode -> ndarray -> OCR
```

when an in-memory image can be passed directly.

Prefer contiguous reusable buffers and direct ndarray/native-buffer paths.

### Keep fast and accurate paths separable

Do not force expensive orientation detection, enhancement, or retries onto every request.

The common case should stay fast.

### Platform boundaries

Keep Windows-only capture/hotkey/clipboard/tray code separated from the OCR core.

Core OCR and benchmark code should remain testable without Windows APIs.

### Dependencies

Add dependencies only when they have clear value.

For every heavy dependency, consider:

- startup cost
- memory cost
- packaging cost
- binary size
- platform impact

Avoid heavy GUI frameworks unless justified by measurement or implementation need.

---

## 5. Test rules

Before considering a task complete:

```powershell
pytest -q
```

When OCR dependencies/models are available, also run the relevant real command.

For benchmark-related changes, run or preserve compatibility with:

```powershell
textj-bench <image> --runs 20 --warmups 2
textj-bench-suite <manifest> --runs 10 --warmups 1
```

Do not make tests require model downloads unless explicitly marked as integration tests.

Core tests should use fake backends where possible.

---

## 6. Definition of done

A development item is done only when:

- implementation exists,
- errors are handled reasonably,
- tests exist for logic that can be tested,
- docs/status are updated,
- no known regression is intentionally hidden,
- performance claims have evidence,
- the repository remains runnable from a clean environment.

See `docs/DEFINITION_OF_DONE.md` for the full checklist.

---

## 7. Work logging

After a meaningful batch of work, update:

`docs/DEV_WORKLOG.md`

Record:

- date
- commit or working state
- what changed
- tests run
- benchmark result if any
- known problems
- next task

Do not turn the worklog into long prose. Keep it operational.

Also update `docs/STATUS.md` when the real project state changes.

---

## 8. Priority order

Use `docs/EXECUTION_PLAN.md` as the main queue.

Unless evidence suggests otherwise, prioritize:

1. stabilize/test the existing core
2. finish reproducible benchmark infrastructure
3. build the resident OCR runtime
4. make clipboard OCR use the resident runtime
5. implement Windows global hotkey
6. implement region selection + direct in-memory capture
7. optimize the measured bottleneck
8. improve Korean/English quality regressions
9. package a reliable Windows build

The official version roadmap remains in `docs/ROADMAP.md`.

---

## 9. Things not to do yet

Do not spend major effort on:

- a custom OCR foundation model
- cloud accounts/sync
- translation
- summarization
- document management
- Electron-style heavy UI
- broad cross-platform UI before Windows works
- speculative GPU rewrites before CPU baseline measurement
- aesthetic UI work before the capture-to-clipboard path works

---

## 10. When blocked

If real Windows validation is unavailable:

1. write unit-testable platform abstractions,
2. add fake/mock implementations,
3. document the exact manual validation command,
4. continue with another independent task.

If model download/network access is unavailable:

1. keep unit tests backend-independent,
2. do not fake benchmark numbers,
3. record that real OCR validation is pending.

Never invent performance results.

---

## 11. Safe autonomy

Normal source edits, tests, docs, refactors, benchmark tooling, and non-destructive repository improvements are expected.

Do not:

- force-push or rewrite history,
- delete large project sections without necessity,
- remove user work merely to simplify the codebase,
- silently change the product goal,
- publish secrets or private local data,
- commit downloaded OCR model binaries unless explicitly intended.

---

## 12. Handoff expectation

At the end of a long session, leave TextJ so another agent can continue without reconstructing context.

At minimum update:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`

and leave the next concrete tasks in `docs/EXECUTION_PLAN.md` accurate.
