# TextJ Development Worklog

Keep newest entries first.

---

## 2026-09-24 — ORT threads experiment, preserve_indent option

- measured `intra_op_num_threads` -1/1/2/4: default (-1) kept; 2 threads
  faster on the 171×92 crop only (38.8 vs 60.8 ms p50)
- added opt-in `options.preserve_indent` (protocol v1 additive field, MCP arg):
  code-py-001 CER 0.0741 → 0.0000; screen-en-001 0.0632 → 1.4105 (so opt-in)
- tests: 99 passed; integration (bundled models): 8 passed, 3 skipped (Korean)

---

## 2026-09-24 — Protocol v1, resident runtime, transports, MCP, benchmarks

### State

Branch `claude/elegant-edison-w7x1z4`, commits after `0a7743b`.

### Changed

- fix: RapidOCR backend crashed (`float(None)`) on every real call because
  the skipped classifier stage is reported as `None`
- backend profiles `ppocrv5-mobile` / `ppocrv6-small`, detector limit options
- `textj.api`: protocol v1 request/response, 13 error codes, limits, image loader
- `textj.runtime.TextJRuntime`: warm backends, bounded admission, BUSY,
  TIMEOUT, batch, status counters
- transports: `textj-serve --stdio|--tcp`, `TextJClient`, `textj-client`
- `textj-mcp` (dependency-free MCP stdio server)
- benchmarks: `textj-bench-compare`, `textj-bench-runtime`, suite `--tags`,
  richer artifact metadata, 11-case synthetic fixture corpus
- default detector policy `max 1280` (measured)
- `docs/AI_TOOL_PROTOCOL.md` rewritten as the implemented v1 spec;
  new `docs/BENCHMARK_RESULTS.md`

### Tests

`pytest -q` → 96 passed (no model downloads). Runtime tests repeated 15x for flakiness.

### Real runs (Linux, 4 vCPU, PP-OCRv6 small, English)

- suite (8 non-Korean fixtures): mean p50 806.6 → 149.6 ms, CER 0.0181 → 0.0181
  (RapidOCR default det policy → `max 1280`)
- runtime 552×131: p50 157.4 ms (Python API) / 168.1 ms (TCP path)
- runtime 1280×720: p50 418.9 ms; detect ≈ 332 ms
- burst 4 clients: max_inflight 1 → 5.91 req/s; 2 → 4.70; 4 → 4.36
- end-to-end verified: stdio, TCP daemon + client, MCP → daemon

### Known problems / blockers

- Korean model download blocked (modelscope.cn, huggingface.co denied by
  sandbox proxy). KO/MIX unmeasured.
- no Windows validation
- code indentation / repeated spaces lost in recognition
- the sandbox proxy logged connection attempts to
  `mobile.events.data.microsoft.com`; could not be reproduced from any TextJ
  process (onnxruntime import/session, rapidocr, cv2, pytest, benchmarks all
  checked) — likely another sandbox process. Re-check on target machine that
  TextJ makes no network calls after models are cached.

### Next

See "Next concrete tasks" in `docs/EXECUTION_PLAN.md` (Korean validation,
HARD/XL fixtures, ORT thread sweep, code/terminal whitespace fidelity).

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
