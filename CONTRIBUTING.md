# Contributing to TextJ

TextJ is an AI-facing, latency-sensitive local OCR tool.

## Product rule

Optimize for:

```text
machine request -> structured OCR response
```

not human UI polish.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
```

## Read first

- `CLAUDE.md`
- `docs/PRODUCT.md`
- `docs/AI_TOOL_PROTOCOL.md`
- `docs/STATUS.md`
- `docs/EXECUTION_PLAN.md`
- `docs/DEFINITION_OF_DONE.md`

## PR expectations

Describe:

- what changed
- why
- tests
- protocol/schema impact
- known limitations

For performance changes include when possible:

- p50
- p95
- CER
- RSS
- request/input configuration
- transport/runtime configuration

## API stability

Machine-facing schemas are public behavior.

Do not silently rename:

- fields
- error codes
- operations
- protocol versions

When breaking changes are unavoidable, version them.

## Dependencies

Keep headless deployment lean.

Avoid adding GUI frameworks.

Before adding a dependency consider:

- startup cost
- RSS
- package size
- cross-platform impact
- daemon deployment impact

## Testing

Use fake backends for protocol/runtime logic.

Unit tests should not download OCR models.

Real OCR belongs in integration validation.

## Data

Do not commit:

- private screenshots
- secrets
- model caches by accident
- unlicensed datasets

Prefer purpose-built fixtures.

## Continuity

After meaningful work update:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`
- `docs/EXECUTION_PLAN.md`
