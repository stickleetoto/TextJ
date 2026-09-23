## Summary

<!-- What changed and why? -->

## Validation

- [ ] `pytest -q`
- [ ] relevant CLI smoke test
- [ ] docs/status updated if project state changed

Commands/results:

```text
paste commands/results here
```

## Performance impact

<!-- Required for performance-sensitive changes. Otherwise write N/A. -->

Hardware/provider:

```text
CPU:
GPU:
ONNX Runtime provider:
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

- [ ] no performance claim is based only on an unrepresentative single run
- [ ] accuracy impact was checked when OCR behavior changed

## Windows / UX checks

When relevant:

- [ ] clipboard contention/failure path considered
- [ ] DPI scaling considered
- [ ] multi-monitor coordinates considered
- [ ] temporary image files avoided
- [ ] resources/hotkeys/handles are cleaned up

## Known limitations

<!-- Explicitly record anything still incomplete or requiring manual validation. -->
