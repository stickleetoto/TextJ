from pathlib import Path

import pytest

from textj.app.serve import build_parser, parse_with_config, runtime_config
from textj.config import ConfigError, load_config


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "textj.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_config_sets_defaults_and_flags_override(tmp_path: Path) -> None:
    path = write(tmp_path, """
config_version = 1
[runtime]
language = "en"
profile = "ppocrv6-small"
max_queue = 3
warmup = false
[limits]
max_batch_items = 5
default_timeout_ms = 1000
[server]
port = 5000
auth = false
""")
    args, limits = parse_with_config(build_parser(), ["--config", str(path), "--max-queue", "7"])
    config = runtime_config(args, limits)

    assert config.language == "en"
    assert config.profile == "ppocrv6-small"
    assert config.max_queue == 7          # flag wins over file
    assert config.warmup is False
    assert config.limits.max_batch_items == 5
    assert config.limits.default_timeout_ms == 1000
    assert config.limits.max_image_side == 16384  # untouched default
    assert args.port == 5000 and args.no_auth is True


def test_no_config_keeps_defaults() -> None:
    args, limits = parse_with_config(build_parser(), [])
    assert runtime_config(args, limits).max_queue == 8
    assert args.det_limit_type == "max" and args.det_limit_side_len == 1280


@pytest.mark.parametrize("text, message", [
    ("[runtime]\nmax_qeue = 1\n", "unknown key"),
    ("[runtme]\n", "unknown top-level"),
    ("[runtime]\nmax_queue = \"8\"\n", "must be int"),
    ("[runtime]\nwarmup = 1\n", "must be bool"),
    ("[limits]\nmax_batch_items = true\n", "must be int"),
    ("[limits]\nmax_batch_items = 0\n", "positive"),
    ("config_version = 2\n", "config_version"),
    ("not toml = = 1", "invalid TOML"),
])
def test_invalid_config_is_rejected(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, text))


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.toml")


def test_serve_main_reports_config_errors(tmp_path: Path, capsys) -> None:
    from textj.app.serve import main

    assert main(["--config", str(write(tmp_path, "[x]\n"))]) == 2
    assert "unknown top-level" in capsys.readouterr().err


def test_example_config_is_valid() -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "textj.toml"
    config = load_config(example)
    assert config["runtime"]["language"] == "ko-en"
