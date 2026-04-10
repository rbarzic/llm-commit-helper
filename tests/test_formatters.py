"""Tests for formatters: generic, python, verilog."""

import pytest
from unittest.mock import patch

from llm_commit_helper.formatters.generic_fmt import format_generic_diff, _hunk_is_formatting_only
from llm_commit_helper.formatters.verilog_fmt import _has_auto_macros


@pytest.mark.parametrize(
    ("removed", "added", "expected"),
    [
        (["hello world\n"], ["hello  world\n"], True),   # extra space
        (["x = 1\n"], ["x  =  1\n"], True),              # whitespace only
        (["a = 1\n"], ["a = 2\n"], False),               # logic change
        ([], [], True),                                   # empty
        (["foo\n"], ["bar\n"], False),                    # content change
    ],
)
def test_hunk_is_formatting_only(
    removed: list[str], added: list[str], expected: bool
) -> None:
    assert _hunk_is_formatting_only(removed, added) == expected


def test_generic_diff_identical_content() -> None:
    content = "line1\nline2\n"
    diff, is_fmt = format_generic_diff("file.txt", content, content)
    assert is_fmt is True
    assert diff == ""


def test_generic_diff_logic_change() -> None:
    old = "x = 1\n"
    new = "x = 2\n"
    diff, is_fmt = format_generic_diff("file.txt", old, new)
    assert is_fmt is False
    assert "x = 1" in diff or "x = 2" in diff


def test_generic_diff_whitespace_only() -> None:
    old = "x = 1\n"
    new = "x  =  1\n"
    diff, is_fmt = format_generic_diff("file.txt", old, new)
    assert is_fmt is True


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("module foo (/*AUTOARG*/);", True),
        ("input /*AUTOINPUT*/;", True),
        ("output /*AUTOOUTPUT*/;", True),
        ("AUTOINST", True),
        ("// normal verilog code", False),
        ("assign a = b;", False),
    ],
)
def test_has_auto_macros(content: str, expected: bool) -> None:
    assert _has_auto_macros(content) == expected


def test_verilog_diff_no_auto_fallback() -> None:
    """Without AUTO macros, verilog formatter uses generic diff."""
    old = "assign x = 1;\n"
    new = "assign x = 2;\n"
    from llm_commit_helper.formatters.verilog_fmt import format_verilog_diff

    diff, is_fmt = format_verilog_diff("chip.v", old, new)
    assert is_fmt is False
    assert "x = 1" in diff or "x = 2" in diff


def test_verilog_diff_auto_emacs_missing() -> None:
    """If emacs is not available, falls back to generic formatter."""
    old = "module foo (/*AUTOARG*/);\nassign x = 1;\n"
    new = "module foo (/*AUTOARG*/);\nassign x = 2;\n"
    from llm_commit_helper.formatters.verilog_fmt import format_verilog_diff

    with patch("llm_commit_helper.formatters.verilog_fmt._run_emacs_delete_auto", return_value=False):
        diff, is_fmt = format_verilog_diff("chip.v", old, new)
    # Should still produce a diff (via generic fallback)
    assert diff != ""


# Local Variables:
# eval: (blacken-mode)
# End:
