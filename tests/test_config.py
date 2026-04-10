"""Tests for config.py: JSONC parsing and Config loading."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from llm_commit_helper.config import (
    _strip_jsonc_comments,
    _parse_jsonc,
    load_config,
    Config,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_TOTAL_SIZE,
)


@pytest.mark.parametrize(
    ("input_text", "expected_keys"),
    [
        ('{"a": 1}', {"a": 1}),
        ('{"a": 1, // comment\n"b": 2}', {"a": 1, "b": 2}),
        ('{"a": 1,}', {"a": 1}),
        ('{"a": [1, 2,]}', {"a": [1, 2]}),
        ('// full line comment\n{"x": 42}', {"x": 42}),
    ],
)
def test_parse_jsonc(input_text: str, expected_keys: dict) -> None:
    result = _parse_jsonc(input_text)
    assert result == expected_keys


def test_strip_jsonc_comments_preserves_urls() -> None:
    text = '{"url": "http://example.com"}'
    result = _strip_jsonc_comments(text)
    # URL double-slash should not be stripped (inside a string)
    assert "http://example.com" in result


def test_load_config_defaults() -> None:
    with patch("llm_commit_helper.config._candidate_paths", return_value=[]):
        cfg = load_config()
    assert cfg.exclude_patterns == []
    assert cfg.max_file_size == DEFAULT_MAX_FILE_SIZE
    assert cfg.max_total_size == DEFAULT_MAX_TOTAL_SIZE
    assert cfg.source is None


def test_load_config_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.jsonc"
    config_file.write_text(
        '{"version": 1, "rules": {"exclude": ["*.netlist.v"], "max_total_size": 5000}}'
    )
    cfg = load_config(config_path=config_file)
    assert "*.netlist.v" in cfg.exclude_patterns
    assert cfg.max_total_size == 5000
    assert cfg.source == config_file


def test_load_config_missing_file_uses_defaults(tmp_path: Path) -> None:
    cfg = load_config(config_path=tmp_path / "nonexistent.jsonc")
    assert cfg.exclude_patterns == []


def test_load_config_invalid_json_uses_defaults(tmp_path: Path) -> None:
    bad_file = tmp_path / "config.jsonc"
    bad_file.write_text("{this is not valid}")
    cfg = load_config(config_path=bad_file)
    assert cfg.exclude_patterns == []


# Local Variables:
# eval: (blacken-mode)
# End:
