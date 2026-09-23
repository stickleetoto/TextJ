# Claude Kickoff Prompt

This file is optional convenience text for starting a fresh Claude development session.

Copy the prompt below if the environment does not automatically load `CLAUDE.md`.

---

You are taking over development of the TextJ repository.

Read `CLAUDE.md`, then read:

- `docs/HANDOFF_CLAUDE.md`
- `docs/STATUS.md`
- `docs/EXECUTION_PLAN.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/PERFORMANCE.md`

Then continue implementation autonomously.

Do not only produce a plan. Inspect the repository, run available tests, fix problems, implement the next highest-value unblocked items, test them, update `docs/STATUS.md` and `docs/DEV_WORKLOG.md`, and continue until reaching a meaningful checkpoint or hard blocker.

The product north star is:

```text
global hotkey
-> select screen region
-> release
-> local OCR
-> text immediately in clipboard
```

Prioritize real end-to-end latency, local processing, Korean/English mixed text, a warm resident runtime, direct in-memory capture, reproducible benchmarks, and reliability.

Do not fabricate benchmark results. Do not rewrite the project without evidence. Do not start custom OCR model research before the v1 product path is working and measured.
