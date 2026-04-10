"""Tests for git_staged.py: file classification and content retrieval."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from llm_commit_helper.git_staged import (
    _parse_name_status,
    classify_file,
    FileKind,
    FileStatus,
    StagedFile,
)
from llm_commit_helper.config import Config


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("M\tpath/to/file.py", [("M", "path/to/file.py", None)]),
        ("A\tnew_file.v", [("A", "new_file.v", None)]),
        ("D\told.py", [("D", "old.py", None)]),
        ("R100\told.py\tnew.py", [("R", "new.py", "old.py")]),
        ("", []),
    ],
)
def test_parse_name_status(line: str, expected: list) -> None:
    result = _parse_name_status(line)
    assert result == expected


@pytest.fixture
def git_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def base_config() -> Config:
    return Config()


def _make_file(path: str, status: FileStatus = FileStatus.MODIFIED) -> StagedFile:
    return StagedFile(path=path, status=status)


def test_classify_added_file(git_root: Path, base_config: Config) -> None:
    f = _make_file("src/new.py", FileStatus.ADDED)
    with patch("llm_commit_helper.git_staged._file_size_in_index", return_value=0):
        kind = classify_file(f, base_config, git_root)
    assert kind == FileKind.ADDED


def test_classify_deleted_file(git_root: Path, base_config: Config) -> None:
    f = _make_file("src/old.py", FileStatus.DELETED)
    kind = classify_file(f, base_config, git_root)
    assert kind == FileKind.DELETED


def test_classify_excluded_by_pattern(git_root: Path) -> None:
    config = Config(exclude_patterns=["*.netlist.v"])
    f = _make_file("chip.netlist.v", FileStatus.MODIFIED)
    kind = classify_file(f, config, git_root)
    assert kind == FileKind.EXCLUDED


def test_classify_excluded_by_glob(git_root: Path) -> None:
    config = Config(exclude_patterns=["sim/firmware_ctests/**"])
    f = _make_file("sim/firmware_ctests/test_foo.c", FileStatus.MODIFIED)
    kind = classify_file(f, config, git_root)
    assert kind == FileKind.EXCLUDED


def test_classify_too_large(git_root: Path, base_config: Config) -> None:
    f = _make_file("big.v", FileStatus.MODIFIED)
    config = Config(max_file_size=100)
    with patch("llm_commit_helper.git_staged._file_size_in_index", return_value=1000):
        with patch("llm_commit_helper.git_staged._is_binary", return_value=False):
            kind = classify_file(f, config, git_root)
    assert kind == FileKind.TOO_LARGE


def test_classify_submodule(git_root: Path, base_config: Config) -> None:
    f = StagedFile(
        path="support/imported/socbuilder",
        status=FileStatus.MODIFIED,
        is_submodule=True,
    )
    kind = classify_file(f, base_config, git_root)
    assert kind == FileKind.SUBMODULE


def test_classify_modified(git_root: Path, base_config: Config) -> None:
    f = _make_file("src/normal.py", FileStatus.MODIFIED)
    with patch("llm_commit_helper.git_staged._file_size_in_index", return_value=100):
        with patch("llm_commit_helper.git_staged._is_binary", return_value=False):
            kind = classify_file(f, base_config, git_root)
    assert kind == FileKind.MODIFIED


# Local Variables:
# eval: (blacken-mode)
# End:
