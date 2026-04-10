"""Tests for submodule.py: log retrieval and formatting."""

import pytest
from pathlib import Path
from unittest.mock import patch

from llm_commit_helper.submodule import get_submodule_log, format_submodule_section


def test_get_submodule_log_no_hashes(tmp_path: Path) -> None:
    result = get_submodule_log("sub/path", None, None, tmp_path)
    assert result == []


def test_get_submodule_log_uninitialized(tmp_path: Path) -> None:
    # Submodule path doesn't exist on disk
    result = get_submodule_log("missing/sub", "abc1234", "def5678", tmp_path)
    assert result == []


def test_get_submodule_log_success(tmp_path: Path) -> None:
    sub_path = tmp_path / "mysub"
    sub_path.mkdir()

    log_output = "abc1234 Fix bug\ndef5678 Add feature\n"
    with patch("llm_commit_helper.submodule.run_command", return_value=(0, log_output, "")):
        result = get_submodule_log("mysub", "000", "fff", tmp_path)

    assert len(result) == 2
    assert "Fix bug" in result[0]
    assert "Add feature" in result[1]


def test_get_submodule_log_git_failure(tmp_path: Path) -> None:
    sub_path = tmp_path / "mysub"
    sub_path.mkdir()

    with patch("llm_commit_helper.submodule.run_command", return_value=(1, "", "not a git repo")):
        result = get_submodule_log("mysub", "000", "fff", tmp_path)

    assert result == []


@pytest.mark.parametrize(
    ("old_hash", "new_hash", "log_lines", "expected_fragment"),
    [
        ("abcdef12", "12345678", ["12345678 feat: add X"], "abcdef12 -> 12345678"),
        ("aaaaaaaa", "bbbbbbbb", [], "[no log available]"),
        (None, None, [], "Added at:"),
        ("0000000", "06287f7", [], "Added at:"),
    ],
)
def test_format_submodule_section(
    old_hash: str | None,
    new_hash: str | None,
    log_lines: list[str],
    expected_fragment: str,
) -> None:
    result = format_submodule_section("path/to/sub", old_hash, new_hash, log_lines)
    assert expected_fragment in result
    assert "path/to/sub" in result


# Local Variables:
# eval: (blacken-mode)
# End:
