# Contributing to TextJ

TextJ is a latency-sensitive OCR utility. Contributions should preserve the product goal:

> Hotkey -> region -> OCR -> clipboard with minimal delay.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
```

## Before coding

Read:

- `CLAUDE.md` for engineering constraints
- `docs/STATUS.md` for the factual current state
- `docs/EXECUTION_PLAN.md` for the active queue
- `docs/DEFINITION_OF_DONE.md` for completion criteria

## Pull request expectations

For ordinary code changes, include:

- what changed
- why
- tests run
- known limitations

For performance-sensitive changes, also include:

- benchmark command
- before p50/p95 when available
- after p50/p95 when available
- CER/accuracy impact when applicable
- memory impact when applicable
- hardware/provider configuration

Do not claim speed improvements from isolated inference timing if end-to-end latency regresses.

## Dependencies

Keep the dependency set lean.

Before adding a large dependency, consider:

- import/startup time
- resident RSS
- package size
- Windows packaging impact
- whether a standard library or existing dependency is sufficient

## Platform code

Windows-specific implementation belongs in Windows/capture/desktop integration modules rather than generic OCR core code.

Keep pure logic independently testable.

## Benchmark changes

Preserve benchmark reproducibility.

Do not silently change:

- normalization rules
- percentile semantics
- benchmark warmup semantics
- ground-truth interpretation

If such behavior must change, document it and update regression tests.

## Test policy

Unit tests should avoid requiring OCR model downloads.

Use fake backends for core logic.

Real-model and Windows integration validation may be documented separately when the environment cannot execute them.

## Data policy

Do not commit:

- private screenshots
- credentials
- local paths containing sensitive information
- downloaded model caches without an explicit repository decision
- copyrighted benchmark sets without permission

Prefer purpose-built benchmark fixtures.

## Documentation

After meaningful batches, keep these accurate:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`
- `docs/EXECUTION_PLAN.md`

A future developer should be able to continue from the repository alone.
