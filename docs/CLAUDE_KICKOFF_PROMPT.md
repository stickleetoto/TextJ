# Claude Kickoff Prompt

Use this when starting a fresh Claude Code development session.

---

You are taking over development of TextJ.

Important direction: **TextJ is an AI-facing local OCR tool/service, not primarily a human desktop OCR application.**

Read these files first:

1. `CLAUDE.md`
2. `docs/HANDOFF_CLAUDE.md`
3. `docs/STATUS.md`
4. `docs/PRODUCT.md`
5. `docs/AI_TOOL_PROTOCOL.md`
6. `docs/EXECUTION_PLAN.md`
7. `docs/ROADMAP.md`
8. `docs/ARCHITECTURE.md`
9. `docs/PERFORMANCE.md`

Then work autonomously.

Do not only produce a plan.

Start by validating the existing repository and tests. Fix any breakage you find. Then continue through the highest-value unblocked items in `docs/EXECUTION_PLAN.md`.

The north star is:

```text
AI agent / automation
-> sends image or screenshot
-> long-lived local TextJ runtime
-> structured OCR result with text, confidence, boxes, timings and stable errors
```

Prioritize:

- stable machine-facing protocol
- resident warm runtime
- local IPC/API
- batch OCR
- bounded concurrency/backpressure
- deterministic error codes
- MCP adapter
- reproducible p50/p95/CER benchmarks
- direct in-memory paths
- Korean + English
- headless reliability

Do not prioritize:

- tray UI
- global hotkeys
- drag-selection UI
- desktop polish
- custom OCR foundation-model research

Human CLI and clipboard code are secondary adapters/debugging utilities.

Do not invent benchmark numbers. Use fake backends for protocol/runtime tests when real OCR/model execution is unavailable.

After meaningful work, update `docs/STATUS.md`, `docs/DEV_WORKLOG.md`, and task state in `docs/EXECUTION_PLAN.md`.

Continue implementation until a meaningful checkpoint or hard blocker.
