# Definition of Done

Use this checklist for meaningful TextJ development tasks.

A task does not need every item below if an item is genuinely irrelevant, but skipping relevant validation should be explicit.

## Correctness

- implementation matches the intended behavior
- invalid input has a defined failure path
- no silent destructive fallback
- Unicode text is preserved
- platform-specific behavior is guarded appropriately

## Tests

- unit tests exist for pure logic
- regression test added for a fixed bug when practical
- tests do not require network/model downloads unless clearly integration-only
- `pytest -q` passes in the available environment

## OCR integration

When the task touches actual OCR:

- Korean path considered
- English/mixed path considered
- empty OCR handled
- confidence behavior considered
- reading order not silently assumed if relevant

## Performance

When the task claims or affects performance:

- before/after measurement where possible
- p50 and p95 preferred
- accuracy impact considered
- memory impact considered
- benchmark configuration recorded
- no fabricated numbers

## Windows UX

When the task touches desktop integration:

- DPI considered
- multi-monitor considered
- cancellation/error path considered
- clipboard lock/contention considered
- no unnecessary temporary files
- cleanup/unregister/close behavior implemented

## Maintainability

- backend abstraction preserved
- Windows-specific code does not leak unnecessarily into OCR core
- dependency addition justified
- public/config behavior documented
- obvious dead code removed

## Documentation

Update when relevant:

- `docs/STATUS.md`
- `docs/DEV_WORKLOG.md`
- `docs/ROADMAP.md`
- user-facing README

## Git hygiene

- commits have meaningful messages
- no downloaded model/cache binaries accidentally committed
- no secrets/private screenshots committed
- no force push for ordinary development
