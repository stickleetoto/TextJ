# TextJ Development Worklog

Keep newest entries first.

---

## 2026-09-24 — Product direction corrected to AI-first OCR tooling

### Direction

TextJ is now explicitly defined as an AI-facing local OCR tool/service.

Primary path:

```text
AI caller -> warm TextJ runtime -> structured OCR response
```

Human desktop UX is secondary.

### Documentation rewritten

- root `CLAUDE.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/AI_TOOL_PROTOCOL.md`
- `docs/ROADMAP.md`
- `docs/EXECUTION_PLAN.md`
- `docs/HANDOFF_CLAUDE.md`
- `docs/STATUS.md`
- `docs/PERFORMANCE.md`
- `docs/CLAUDE_KICKOFF_PROMPT.md`
- README/docs index
- definition of done

### New priority

1. validate core
2. benchmark regression
3. protocol v1
4. resident runtime
5. local machine API
6. batch/concurrency
7. MCP adapter
8. optimization
9. headless packaging

### Deprioritized

- tray
- global hotkey
- drag-selection UI
- desktop polish

Existing clipboard code remains as a useful adapter/test path.

---

## 2026-09-24 — Initial Claude handoff foundation

### Baseline

`6bcf98f7f4593c291ff1c02f0c7b4ccad5ca26a1`

### Existing implementation

- RapidOCR / PP-OCRv5 baseline
- file OCR
- ndarray OCR
- benchmark CLI
- benchmark suite
- CER
- sampled RSS
- clipboard prototype

### Note

The original handoff was desktop-UX oriented and was superseded by the AI-first direction above.
