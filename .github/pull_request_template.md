## Summary

<!-- What changed and why? -->

## Validation

- [ ] `pytest -q`
- [ ] relevant CLI/API smoke test
- [ ] docs/status updated if project state changed

Commands/results:

```text
paste commands/results here
```

## Protocol / API impact

- [ ] no machine-facing schema change
- [ ] or schema/protocol change is documented and versioned
- [ ] error-code behavior is covered by tests when changed
- [ ] stdout protocol output remains machine-parseable

Notes:

<!-- Describe request/response changes, compatibility, limits, or N/A. -->

## Performance impact

<!-- Required for performance-sensitive changes. Otherwise write N/A. -->

Environment:

```text
CPU:
GPU:
provider:
transport:
input:
```

Before:

```text
p50:
p95:
CER:
RSS:
```

After:

```text
p50:
p95:
CER:
RSS:
```

- [ ] no speed claim is based on a single lucky run
- [ ] total request latency was considered, not only model inference
- [ ] accuracy impact was checked when OCR behavior changed

## Runtime / load checks

When relevant:

- [ ] backend is not reconstructed per request
- [ ] queue is bounded
- [ ] BUSY/timeout behavior is deterministic
- [ ] malformed requests are bounded
- [ ] daemon/API is local-only by default
- [ ] shutdown/cleanup is handled

## Known limitations

<!-- Explicitly record manual-validation needs or remaining blockers. -->
