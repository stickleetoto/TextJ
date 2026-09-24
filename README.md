# TextJ

**Ultra-fast local OCR for AI agents and automated toolchains.**

TextJ is designed around one rule:

> **Give an AI system an image and return structured OCR as quickly and predictably as possible.**

TextJ is not primarily a desktop OCR app.

The main consumers are:

- LLM agents
- computer-use agents
- automation workers
- local AI runtimes
- MCP tools
- screenshot/UI analysis pipelines

## Target architecture

```text
AI Agent
   |
   +-- Python API
   +-- JSON stdio
   +-- local daemon
   +-- MCP adapter
          |
          v
   TextJ warm runtime
          |
          v
      OCR backend
          |
          v
 structured OCR result
```

## Current status

**OCR core exists. Benchmark foundation is in progress. AI protocol + resident runtime are next.**

Current implementation includes:

- RapidOCR / PP-OCRv5 baseline
- Korean/English-capable OCR path
- file input
- in-memory ndarray input
- text / confidence / boxes
- JSON output
- latency benchmarks
- p50/p95
- CER
- sampled RSS
- benchmark suites
- an older clipboard adapter useful for manual tests

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

## Current debug CLI

```powershell
textj screenshot.png --json
textj-bench screenshot.png --runs 20 --warmups 2
textj-bench-suite benchmarks/manifest.json --runs 10 --warmups 1
```

These commands are development/debug interfaces.

The intended v1 interface is machine-facing and long-lived.

## Planned machine-facing request

Conceptually:

```json
{
  "protocol_version": "1",
  "request_id": "req-1",
  "operation": "ocr",
  "input": {
    "type": "path",
    "path": "frame.png"
  },
  "options": {
    "language": "korean",
    "include_boxes": true
  }
}
```

Response:

```json
{
  "protocol_version": "1",
  "request_id": "req-1",
  "ok": true,
  "result": {
    "text": "recognized text",
    "lines": [],
    "backend": "rapidocr-onnx",
    "timings_ms": {}
  }
}
```

See [AI Tool Protocol](docs/AI_TOOL_PROTOCOL.md).

## Project goals

- very low warm request latency
- local/offline OCR
- Korean + English mixed text
- stable structured schemas
- warm resident model/runtime
- batch OCR
- bounded concurrency
- machine-readable errors
- backend independence
- MCP/agent integration
- reproducible performance/accuracy benchmarks

## Not the main goal

These are optional or lower priority:

- tray UI
- global hotkey
- drag-select overlay
- human OCR history
- desktop polish

## Autonomous development

- [Claude instructions](CLAUDE.md)
- [Claude handoff](docs/HANDOFF_CLAUDE.md)
- [Execution plan](docs/EXECUTION_PLAN.md)
- [AI Tool Protocol](docs/AI_TOOL_PROTOCOL.md)
- [Definition of done](docs/DEFINITION_OF_DONE.md)
- [Development worklog](docs/DEV_WORKLOG.md)

## Documentation

- [Docs index](docs/README.md)
- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Performance](docs/PERFORMANCE.md)
- [Benchmark matrix](docs/BENCHMARK_MATRIX.md)
- [OCR engine](docs/OCR_ENGINE.md)
- [Optimization](docs/OPTIMIZATION.md)
- [Technology radar](docs/TECH_RADAR.md)

## License

MIT
