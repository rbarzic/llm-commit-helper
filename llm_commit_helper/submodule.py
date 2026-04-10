"""Submodule log: fetch commit log between old and new hashes."""

import sys
from pathlib import Path
from typing import Optional

from llm_commit_helper.utils import run_command


_NULL_HASH = set(["0" * 7, "0" * 8, "0" * 40])


def _is_null_hash(h: str) -> bool:
    """Return True if hash is the all-zeros null hash (new submodule addition)."""
    return not h.strip("0")


def get_submodule_log(
    submodule_path: str,
    old_hash: Optional[str],
    new_hash: Optional[str],
    git_root: Path,
) -> list[str]:
    """Return one-line log entries for a submodule update.

    For a newly added submodule (old hash is null), returns the last few
    commits of new_hash instead of an old..new range.
    Returns an empty list if the submodule is uninitialized or hashes are missing.
    """
    if not old_hash or not new_hash:
        return []

    abs_path = git_root / submodule_path
    if not abs_path.is_dir():
        print(
            f"[llm-commit-helper] Submodule not initialized: {submodule_path}",
            file=sys.stderr,
        )
        return []

    if _is_null_hash(old_hash):
        # Newly added submodule — show the tip commit only
        rc, out, err = run_command(
            ["git", "log", "--oneline", "-5", new_hash],
            cwd=abs_path,
        )
    else:
        rc, out, err = run_command(
            ["git", "log", "--oneline", f"{old_hash}..{new_hash}"],
            cwd=abs_path,
        )

    if rc != 0:
        print(
            f"[llm-commit-helper] Could not get submodule log for {submodule_path}: {err.strip()}",
            file=sys.stderr,
        )
        return []

    lines = [line for line in out.splitlines() if line.strip()]
    return lines


def format_submodule_section(
    submodule_path: str,
    old_hash: Optional[str],
    new_hash: Optional[str],
    log_lines: list[str],
) -> str:
    """Format the submodule section for output."""
    new_short = (new_hash or "?")[:8]
    is_new = not old_hash or _is_null_hash(old_hash)

    if is_new:
        lines = [
            f"--- Submodule: {submodule_path} ---",
            f"Added at: {new_short}",
        ]
    else:
        old_short = (old_hash or "?")[:8]
        lines = [
            f"--- Submodule: {submodule_path} ---",
            f"Updated: {old_short} -> {new_short}",
        ]

    if log_lines:
        for entry in log_lines:
            lines.append(f"  {entry}")
    else:
        lines.append("  [no log available]")
    return "\n".join(lines)


# Local Variables:
# eval: (blacken-mode)
# End:
