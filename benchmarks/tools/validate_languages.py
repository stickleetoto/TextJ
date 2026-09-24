"""Validate TextJ English / Korean / mixed OCR end to end and record numbers.

Run from the repository root after installing TextJ:

    textj-models fetch                      # ko-en models (needs network once)
    textj-models fetch --language en        # optional: English PP-OCRv5 recognizer
    python benchmarks/tools/validate_languages.py --runs 10 --warmups 2

Writes ``benchmarks/results/language-validation.json`` and ``.md``.
Configurations whose model files are not cached are reported as skipped;
nothing is downloaded by this script.

Sections:
1. accuracy/latency per tag (EN / KO / MIX / ...) for each configuration
2. offline check: fresh process, TEXTJ_OFFLINE=1, Python audit hook counting
   network events while the runtime starts and OCRs EN, KO and MIX fixtures
3. resident memory: RSS after start (idle) and after OCR, for one ko-en
   runtime, one en runtime, and both resident in one process
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "fixtures"
MANIFEST = FIXTURES / "manifest.json"
RESULTS = ROOT / "benchmarks" / "results"

CONFIGS = [
    # name, profile, language, det_limit_type, det_limit_side_len
    ("v5-ko-en-max1280", "ppocrv5-mobile", "ko-en", "max", 1280),
    ("v5-ko-en-rapidocr-default-det", "ppocrv5-mobile", "ko-en", None, None),
    ("v5-en-max1280", "ppocrv5-mobile", "en", "max", 1280),
    ("v6-en-max1280", "ppocrv6-small", "en", "max", 1280),
]


def models_available(profile: str, language: str) -> bool:
    from textj import model_store

    return all(model_store.find_model(spec) for spec in model_store.specs_for(profile, language))


def run_config(name, profile, language, limit_type, side_len, runs, warmups) -> dict:
    from textj.backends.rapidocr_backend import RapidOCRBackend
    from textj.benchmark_suite import run_suite
    from textj.pipeline import OCRPipeline

    if not models_available(profile, language):
        return {"name": name, "skipped": "model files not cached (run textj-models fetch)"}
    backend = RapidOCRBackend(
        language=language, profile=profile, text_score=0.5,
        det_limit_type=limit_type, det_limit_side_len=side_len, model_download="never",
    )
    suite = run_suite(OCRPipeline(backend), MANIFEST, runs=runs, warmups=warmups).to_dict()
    return {
        "name": name,
        "backend": backend.describe(),
        "by_tag": suite["by_tag"],
        "mean_cer": suite["mean_cer"],
        "cases": [
            {"id": c["id"], "tags": c["tags"], "cer": c["cer"],
             "p50": c["benchmark"]["latency_ms"]["p50"],
             "p95": c["benchmark"]["latency_ms"]["p95"],
             "text": c["recognized_text"]}
            for c in suite["cases"]
        ],
    }


OFFLINE_PROBE = r"""
import json, sys
events = []
def hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "urllib.Request", "http.client.connect"):
        events.append(event)
sys.addaudithook(hook)
from textj.runtime import RuntimeConfig, TextJRuntime
profile, language = sys.argv[1], sys.argv[2]
rt = TextJRuntime(RuntimeConfig(language=language, profile=profile, model_download="never")).start()
out = {}
for name in sys.argv[3:]:
    r = rt.ocr(name)
    out[name] = r["result"]["text"] if r["ok"] else r["error"]["code"]
rt.close()
print(json.dumps({"network_events": len(events), "event_kinds": sorted(set(events)), "results": out}, ensure_ascii=False))
"""

RSS_PROBE = r"""
import json, sys, psutil
from textj.runtime import RuntimeConfig, TextJRuntime
proc = psutil.Process()
base = proc.memory_info().rss
runtimes = []
for spec in sys.argv[1].split(","):
    profile, language = spec.split(":")
    runtimes.append(TextJRuntime(RuntimeConfig(language=language, profile=profile, model_download="never")).start())
idle = proc.memory_info().rss
for rt in runtimes:
    for image in sys.argv[2:]:
        rt.ocr(image)
after = proc.memory_info().rss
print(json.dumps({"python_baseline_mb": base / 2**20, "idle_after_start_mb": idle / 2**20,
                  "after_ocr_mb": after / 2**20}))
"""


def subprocess_json(code: str, args: list[str]) -> dict:
    env = {**os.environ, "TEXTJ_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"}
    completed = subprocess.run([sys.executable, "-c", code, *args], capture_output=True,
                               env=env, timeout=600)
    if completed.returncode != 0:
        return {"error": completed.stderr.decode("utf-8", "replace")[-2000:]}
    return json.loads(completed.stdout.decode("utf-8").strip().splitlines()[-1])


def markdown(report: dict) -> str:
    lines = ["# TextJ language validation", "", f"System: {report['system']}", ""]
    lines += ["| Config | Tag | Cases | p50 ms | p95 ms | CER | max sampled RSS MB |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for config in report["configs"]:
        if "skipped" in config:
            lines.append(f"| {config['name']} | — | — | — | — | — | skipped: {config['skipped']} |")
            continue
        for tag in ("EN", "KO", "MIX", "CODE", "TERM", "URL", "PATH", "NUM", "TINY", "DARK"):
            agg = config["by_tag"].get(tag)
            if agg:
                cer = f"{agg['mean_cer']:.4f}" if agg["mean_cer"] is not None else "-"
                lines.append(f"| {config['name']} | {tag} | {agg['case_count']} | {agg['mean_p50_ms']:.1f} | "
                             f"{agg['mean_p95_ms']:.1f} | {cer} | {agg['max_sampled_rss_mb']:.1f} |")
    lines += ["", "## Offline check", "", "```json",
              json.dumps(report["offline"], ensure_ascii=False, indent=2), "```",
              "", "## Resident memory", "", "```json",
              json.dumps(report["rss"], indent=2), "```", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--output", type=Path, default=RESULTS / "language-validation.json")
    args = parser.parse_args()

    from textj.system_info import collect_system_info

    report: dict = {"system": collect_system_info(), "configs": []}
    for config in CONFIGS:
        print(f"[validate] {config[0]}", file=sys.stderr, flush=True)
        report["configs"].append(run_config(*config, args.runs, args.warmups))

    probe_images = [str(FIXTURES / "images" / f) for f in
                    ("en-url-001.png", "ko-para-001.png", "mix-tech-001.png", "mix-path-001.png")]
    offline_target = ("ppocrv5-mobile", "ko-en") if models_available("ppocrv5-mobile", "ko-en") \
        else ("ppocrv6-small", "en")
    report["offline"] = {"profile": offline_target[0], "language": offline_target[1],
                         **subprocess_json(OFFLINE_PROBE, [*offline_target, *probe_images])}

    rss_specs = []
    if models_available("ppocrv5-mobile", "ko-en"):
        rss_specs.append("ppocrv5-mobile:ko-en")
    if models_available("ppocrv5-mobile", "en"):
        rss_specs.append("ppocrv5-mobile:en")
    rss_specs.append("ppocrv6-small:en")
    report["rss"] = {spec: subprocess_json(RSS_PROBE, [spec, *probe_images]) for spec in rss_specs}
    if len(rss_specs) >= 2:
        both = ",".join(rss_specs[:2])
        report["rss"][both] = subprocess_json(RSS_PROBE, [both, *probe_images])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
