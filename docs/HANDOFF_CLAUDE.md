# Claude Handoff — TextJ

Last prepared: 2026-09-24

## Critical direction correction

TextJ is **not primarily a human-facing OCR app**.

Previous documents emphasized:

```text
hotkey -> drag -> OCR -> clipboard
```

That is no longer the main product direction.

The correct north star is:

```text
AI agent / worker
-> sends image or screenshot
-> warm local TextJ runtime
-> receives structured OCR result
```

TextJ should behave like a fast local infrastructure primitive that other AI systems can call.

Human CLI/clipboard functions are retained as debugging/adapters, not the center of the architecture.

---

## Current implementation

Baseline before this direction rewrite:

`3f5352d5561cd7458528e1780ce87e12e88fce95`

Already implemented:

- Python package
- backend abstraction
- RapidOCR
- PP-OCRv5 mobile baseline
- Korean recognition
- ONNX Runtime CPU
- file input
- ndarray input
- text / score / boxes
- JSON output
- benchmark runner
- p50/p95
- CER
- sampled RSS
- benchmark suite
- clipboard image prototype
- Win32 clipboard output

The clipboard path is no longer a product priority, but useful code should not be deleted just because the priority changed.

---

## First job

1. read `CLAUDE.md`
2. run tests
3. inspect current code for breakage
4. update any remaining desktop-centric assumptions encountered
5. begin `docs/EXECUTION_PLAN.md` from Phase A
6. move quickly toward Protocol v1 and Resident Runtime

---

## New priority

Highest-value upcoming work:

```text
stable OCR core
-> benchmark regression
-> protocol v1
-> warm resident runtime
-> local machine API
-> batch/concurrency
-> MCP adapter
-> measured optimization
-> headless packaging
```

Do not spend primary development time on:

- global hotkeys
- tray UI
- region selection
- desktop UX

---

## AI-facing contract

Read:

`docs/AI_TOOL_PROTOCOL.md`

Public behavior should become stable and versioned.

AI callers need:

- request IDs
- protocol version
- structured results
- stable error codes
- limits
- timeouts
- batch semantics
- concurrency semantics

Do not make callers parse human-formatted console messages.

---

## Runtime architecture

Target:

```text
            +-------------------+
AI client ->| local transport   |
            +---------+---------+
                      |
                      v
            +-------------------+
            | TextJ Runtime     |
            | warm OCR backend  |
            | bounded queue     |
            | timeout policy    |
            +---------+---------+
                      |
                      v
                 OCR pipeline
                      |
                      v
             structured response
```

Adapters such as MCP, stdio, Python API, or clipboard should all reuse the same runtime.

---

## Development behavior

Be implementation-heavy.

Do not stop after making a roadmap when code can be written.

After each meaningful batch:

- test
- benchmark when applicable
- update `docs/STATUS.md`
- update `docs/DEV_WORKLOG.md`
- continue to the next unblocked task

If real OCR/model validation is blocked, work on protocol/runtime logic using fake backends.

Never fabricate benchmark results.
