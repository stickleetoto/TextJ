# TextJ Benchmark Corpus

This directory is the home for local OCR benchmark fixtures.

Large or copyrighted screenshots should not be committed blindly. Prefer small, purpose-built fixtures whose expected text is known.

## Suggested layout

```text
benchmarks/
├─ manifest.json
├─ images/
│  ├─ ko_ui_001.png
│  ├─ mix_code_001.png
│  └─ dark_terminal_001.png
├─ expected/
│  ├─ ko_ui_001.txt
│  ├─ mix_code_001.txt
│  └─ dark_terminal_001.txt
└─ results/
   └─ ...
```

`results/` is ignored by Git.

## Manifest

```json
{
  "cases": [
    {
      "id": "ko-ui-001",
      "image": "images/ko_ui_001.png",
      "expected": "expected/ko_ui_001.txt",
      "tags": ["KO", "UI"]
    }
  ]
}
```

Paths are resolved relative to the manifest.

## Run

```powershell
textj-bench-suite benchmarks/manifest.json --runs 10 --warmups 1
```

Save a reproducible artifact:

```powershell
textj-bench-suite benchmarks/manifest.json \
  --runs 20 \
  --warmups 2 \
  --output benchmarks/results/baseline.json
```

The result includes per-case p50/p95 latency, recognized text, CER when ground truth exists, backend metadata, and system/runtime metadata.
