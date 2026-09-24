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

As of 2026-09-24 (see `docs/STATUS.md` for the authoritative list):

- OCR core + RapidOCR backend (profiles `ppocrv5-mobile`, `ppocrv6-small`)
- protocol v1 (`src/textj/api/`), spec in `docs/AI_TOOL_PROTOCOL.md`
- resident `TextJRuntime` (`src/textj/runtime/`) with bounded queue, BUSY,
  TIMEOUT, batch, status
- transports: `textj-serve --stdio|--tcp`, `TextJClient`, `textj-client`
- MCP adapter `textj-mcp`
- benchmarks: suite, comparator, runtime bench, synthetic fixtures;
  measured numbers in `docs/BENCHMARK_RESULTS.md`
- clipboard code kept as a debug adapter

Blocked in the cloud sandbox: Korean model download (modelscope/HF denied),
Windows validation. Use `--profile ppocrv6-small --language en` for offline
English runs.

## First job

1. read `CLAUDE.md`
2. `pip install -e ".[dev]"` and `pytest -q`
3. read "Next concrete tasks" in `docs/EXECUTION_PLAN.md` and continue there
4. keep every interface on the shared `TextJRuntime` + protocol v1 path

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
