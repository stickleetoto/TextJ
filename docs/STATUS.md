# Development Status

Last updated: 2026-09-24

## Product direction

**TextJ is an AI-facing local OCR tool/service.**

It is not primarily a human desktop OCR application.

Primary target:

```text
AI agent
-> image/screenshot request
-> local warm OCR
-> structured response
```

Human CLI and clipboard paths are secondary adapters/debugging tools.

## Current milestone

**v0.1 OCR Core implemented; v0.2 Benchmark Foundation in progress; protocol/runtime redesign next.**

## Implemented

### OCR core

- Python package
- backend abstraction
- RapidOCR backend
- PP-OCRv5 mobile configuration
- Korean recognition
- ONNX Runtime CPU baseline
- file input
- ndarray input
- text / confidence / boxes
- JSON-capable result model
- internal stage timing where available

### Benchmark foundation

- single-image benchmark
- warmups
- min / mean / p50 / p95 / max
- sampled RSS
- CER
- JSON persistence
- system/runtime metadata
- benchmark manifest
- benchmark suite

### Existing adapters

- CLI
- clipboard image input
- Win32 clipboard text output

Clipboard code is now considered an optional adapter, not the primary product path.

### Agent handoff

- `CLAUDE.md`
- `docs/HANDOFF_CLAUDE.md`
- `docs/EXECUTION_PLAN.md`
- `docs/DEFINITION_OF_DONE.md`
- `docs/DEV_WORKLOG.md`
- `docs/AI_TOOL_PROTOCOL.md`

## Next engineering work

1. clean test/install validation
2. benchmark regression comparator
3. protocol v1 request/response/error models
4. resident TextJRuntime
5. local machine-facing transport
6. batch requests
7. bounded concurrency/backpressure
8. MCP adapter
9. measured OCR optimization
10. headless packaging

## Known limitations

- no protocol v1 implementation yet
- no long-lived runtime yet
- CLI constructs backend per invocation
- no local daemon yet
- no MCP adapter yet
- no batch public API yet
- no defined queue/backpressure behavior yet
- no stable public error-code layer yet
- real Windows/model validation remains incomplete
