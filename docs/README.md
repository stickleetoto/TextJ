# TextJ Documentation

TextJ is an **AI-facing local OCR tool/service**.

Its primary job is to accept image input from an AI agent or automated pipeline and return structured OCR output quickly and predictably.

## Start here

| Document | Purpose |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | Product definition and AI-first scope |
| [STATUS.md](STATUS.md) | Current factual implementation state |
| [ROADMAP.md](ROADMAP.md) | Version milestones |
| [EXECUTION_PLAN.md](EXECUTION_PLAN.md) | Active autonomous development queue |
| [AI_TOOL_PROTOCOL.md](AI_TOOL_PROTOCOL.md) | Draft machine-facing protocol |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Runtime/service architecture |
| [HANDOFF_CLAUDE.md](HANDOFF_CLAUDE.md) | Claude development handoff |

## Performance and OCR engineering

| Document | Purpose |
| --- | --- |
| [PERFORMANCE.md](PERFORMANCE.md) | Request-to-response performance policy |
| [BENCHMARK_MATRIX.md](BENCHMARK_MATRIX.md) | Workloads and benchmark dimensions |
| [OCR_ENGINE.md](OCR_ENGINE.md) | OCR backend strategy |
| [OPTIMIZATION.md](OPTIMIZATION.md) | Optimization ideas and constraints |
| [TECH_STACK.md](TECH_STACK.md) | Runtime and technology candidates |
| [TECH_RADAR.md](TECH_RADAR.md) | Adopt / Trial / Assess / Hold |

## Development continuity

| Document | Purpose |
| --- | --- |
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | Completion criteria |
| [DEV_WORKLOG.md](DEV_WORKLOG.md) | Cross-session worklog |
| [CLAUDE_KICKOFF_PROMPT.md](CLAUDE_KICKOFF_PROMPT.md) | Fresh Claude session bootstrap |

## Secondary adapters

These are useful but not the primary product direction:

| Document | Purpose |
| --- | --- |
| [CLIPBOARD.md](CLIPBOARD.md) | Existing clipboard OCR prototype |
| [WINDOWS_RUNTIME.md](WINDOWS_RUNTIME.md) | Earlier Windows desktop-runtime research |

Clipboard/hotkey/tray/region-selection work should not displace protocol/runtime/API/MCP work unless explicitly requested.

## Core doctrine

```text
AI caller
-> stable request
-> warm local TextJ runtime
-> OCR
-> structured result
```

TextJ is a tool, not a conversational model and not primarily a desktop GUI.
