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

**Protocol v1, the resident runtime, stdio/daemon transports, batch, and an MCP adapter are implemented.**

| Language path | Model | Validation |
| --- | --- | --- |
| English | PP-OCRv6 small (bundled, offline) | real OCR + benchmarks on Linux |
| Korean / Korean+English (default `ko-en`) | PP-OCRv5 Korean recognizer | **not yet validated** — model download was blocked in the dev environment; tests and benchmark tooling are ready |

Windows has not been validated yet. Details: [STATUS](docs/STATUS.md),
[benchmark results](docs/BENCHMARK_RESULTS.md).

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

### Models

```bash
textj-models fetch          # Korean+English (ko-en) models, SHA256-verified, once
textj-models status         # what is cached, where
```

After that TextJ runs fully offline (`TEXTJ_OFFLINE=1` forbids any download).
`--profile ppocrv6-small --language en` needs no download (bundled) but has no
Korean. Cache paths, mirrors and offline import: [docs/MODELS.md](docs/MODELS.md).

### Languages

One runtime loads one recognizer: `ko-en` (default, Korean + English + mixed)
or `en`. Callers do not need to know the image language; the optional request
option `language` (`auto` | `ko-en` | `en`) only asserts what the runtime must serve.

## Use from an agent

### Python API

```python
from textj import RuntimeConfig, TextJRuntime

runtime = TextJRuntime(RuntimeConfig(language="ko-en")).start()    # loads + warms once
response = runtime.ocr("frame.png")                  # or ndarray (BGR) / encoded bytes
if response["ok"]:
    print(response["result"]["text"])
else:
    print(response["error"]["code"])                 # stable machine-readable code
runtime.close()
```

### JSON stdio (long-lived subprocess)

```bash
textj-serve --stdio
# stdin, one JSON object per line:
{"protocol_version":"1","request_id":"r1","operation":"ocr","input":{"type":"path","path":"/abs/frame.png"}}
# stdout, one response per line:
{"protocol_version":"1","request_id":"r1","ok":true,"result":{"text":"...","lines":[...],"timings_ms":{...}}}
```

### Local daemon

```bash
textj-serve --tcp            # loopback only; writes host/port/token to ~/.textj/daemon.json
textj-client status
textj-client ocr frame.png
textj-client ocr a.png b.png c.png     # ocr_batch
```

```python
from textj.transport.client import TextJClient
with TextJClient.from_state_file() as client:
    response = client.ocr_path("frame.png")
```

### MCP

```json
{"mcpServers": {"textj": {"command": "textj-mcp"}}}
```

Tools: `ocr_image`, `ocr_batch`, `textj_status`. Add `"args": ["--daemon"]` to
share an already running `textj-serve --tcp` runtime.

Runtime/daemon settings can come from a TOML file: `textj-serve --config examples/textj.toml`.

Full request/response/error spec: [AI Tool Protocol v1](docs/AI_TOOL_PROTOCOL.md).

## Benchmark / debug commands

```bash
textj image.png --json                                   # one-shot (loads model each run)
textj-bench image.png --runs 20 --warmups 2
textj-bench-suite benchmarks/fixtures/manifest.json --runs 10 --warmups 1 --output base.json
textj-bench-compare base.json new.json --max-p95-regression-pct 10 --max-cer-increase 0.005
textj-bench-runtime image.png --runs 20                  # API/JSON/TCP latency + burst
```

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
- [Benchmark results](docs/BENCHMARK_RESULTS.md)
- [Models](docs/MODELS.md)
- [OCR engine](docs/OCR_ENGINE.md)
- [Optimization](docs/OPTIMIZATION.md)
- [Technology radar](docs/TECH_RADAR.md)

## License

MIT
