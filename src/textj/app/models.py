"""textj-models: inspect, download and import OCR model files.

Examples:
    textj-models status
    textj-models fetch                          # default: ppocrv5-mobile / ko-en
    textj-models fetch --profile ppocrv5-mobile --language en
    textj-models import korean_PP-OCRv5_rec_mobile.onnx
    textj-models path
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from textj import model_store
from textj.languages import normalize_runtime_language


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="textj-models", description=__doc__.split("\n")[0])
    parser.add_argument("--model-dir", type=Path, help="Cache directory override.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show which model files are present and verified.")
    fetch = sub.add_parser("fetch", help="Download (SHA256-verified) model files.")
    fetch.add_argument("--profile", default="ppocrv5-mobile", choices=("ppocrv5-mobile", "ppocrv6-small"))
    fetch.add_argument("--language", default="ko-en", help="ko-en (default) or en.")
    fetch.add_argument("--all", action="store_true", help="Fetch every supported profile/language.")
    imp = sub.add_parser("import", help="Install manually obtained model files (SHA256-checked).")
    imp.add_argument("files", nargs="+", type=Path)
    sub.add_parser("path", help="Print the model cache directory.")
    return parser


def status(cache_dir: Path | None) -> list[dict]:
    rows = []
    for (profile, language) in model_store.PROFILE_MODELS:
        for spec in model_store.specs_for(profile, language):
            path = model_store.find_model(spec, cache_dir)
            rows.append({
                "profile": profile,
                "language": language,
                "task": spec.task,
                "file": spec.filename,
                "sha256": spec.sha256,
                "present": path is not None,
                "path": str(path) if path else None,
                "bundled": spec.bundled,
            })
    return rows


def main(argv: list[str] | None = None) -> int:
    from textj.app.common import ensure_utf8_stdio

    ensure_utf8_stdio()
    args = build_parser().parse_args(argv)
    cache_dir = args.model_dir
    log = (lambda message: print(f"[textj] {message}", file=sys.stderr, flush=True))

    try:
        if args.command == "path":
            payload = {"model_dir": str(cache_dir or model_store.default_cache_dir()),
                       "offline": model_store.offline_mode()}
        elif args.command == "status":
            payload = {"model_dir": str(cache_dir or model_store.default_cache_dir()),
                       "offline": model_store.offline_mode(),
                       "models": status(cache_dir)}
        elif args.command == "fetch":
            pairs = (list(model_store.PROFILE_MODELS) if args.all
                     else [(args.profile, normalize_runtime_language(args.language))])
            fetched = []
            for profile, language in pairs:
                for spec in model_store.specs_for(profile, language):
                    path = model_store.fetch(spec, cache_dir, log=log)
                    fetched.append({"file": spec.filename, "path": str(path)})
            payload = {"fetched": fetched}
        else:
            imported = []
            for file in args.files:
                spec, path = model_store.import_file(file, cache_dir)
                imported.append({"file": spec.filename, "key": spec.key, "path": str(path)})
            payload = {"imported": imported}
    except (model_store.ModelError, ValueError, OSError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"ok": True, **payload}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "status":
        print(f"model dir: {payload['model_dir']} (offline: {payload['offline']})")
        for row in payload["models"]:
            state = "ok" if row["present"] else "MISSING"
            print(f"  {row['profile']:<15} {row['language']:<6} {row['task']:<4} "
                  f"{row['file']:<32} {state:<8} {row['path'] or ''}")
    else:
        for key in ("model_dir", "fetched", "imported"):
            if key in payload:
                print(json.dumps(payload[key], ensure_ascii=False, indent=2)
                      if not isinstance(payload[key], str) else payload[key])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
