# Definition of Done

Use this checklist for meaningful TextJ changes.

## Correctness

- implementation matches intended behavior
- invalid input has deterministic behavior
- machine-facing errors use stable codes when applicable
- Unicode is preserved
- request IDs are preserved through the call path when applicable
- no silent fallback changes result semantics

## Protocol/API

When touching public machine-facing behavior:

- schema is documented
- protocol version behavior is tested
- success and error responses are tested
- malformed input is rejected deterministically
- limits are enforced before expensive work where practical
- stdout protocol output is not polluted by debug logs
- breaking schema changes are not introduced silently

## Runtime

When touching the resident service:

- backend is not accidentally reconstructed per request
- lifecycle is tested
- readiness state is defined
- queue is bounded
- concurrency policy is explicit
- shutdown behavior is defined
- timeout/BUSY behavior is tested

## OCR

When OCR behavior changes:

- Korean considered
- English/mixed considered
- technical text considered
- empty OCR handled
- confidence behavior considered
- boxes/order behavior tested where relevant

## Performance

When claiming or affecting performance:

- p50/p95 measured where possible
- total request latency preferred over isolated inference
- accuracy impact checked
- RSS impact checked
- configuration recorded
- no fabricated numbers

For daemon changes, also consider:

- queue time
- serialization
- transport overhead
- throughput
- overload behavior

## Security

For machine-facing transports:

- local-only default
- no arbitrary command execution
- no unsafe object deserialization
- payload sizes bounded
- malformed requests cannot create unbounded work

## Tests

- `pytest -q` passes where executable
- pure logic uses fake backends where practical
- unit tests do not require model download by default
- fixed bugs gain regression tests when practical

## Maintainability

- OCR backend remains replaceable
- adapters remain thin
- core request/result behavior is not duplicated across adapters
- dependencies are justified
- no GUI dependency is added without a compelling reason

## Documentation

Update relevant:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`
- `docs/EXECUTION_PLAN.md`
- `docs/AI_TOOL_PROTOCOL.md`
- README when public behavior changes

## Git hygiene

- meaningful commits
- no secrets
- no private screenshots
- no accidental model/cache binaries
- no force-push for ordinary work
