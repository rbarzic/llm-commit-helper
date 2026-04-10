"""Generic formatter: per-hunk whitespace normalization."""

import difflib
import re
from typing import Optional

from llm_commit_helper.diff_engine import make_unified_diff, annotate_formatting_hunks


def _normalize_line(line: str) -> str:
    """Strip whitespace and normalize runs of spaces/tabs."""
    return re.sub(r"\s+", " ", line.strip())


def _hunk_is_formatting_only(removed: list[str], added: list[str]) -> bool:
    """Return True if hunk differences are purely whitespace."""
    norm_removed = [_normalize_line(l) for l in removed]
    norm_added = [_normalize_line(l) for l in added]
    return norm_removed == norm_added


def format_generic_diff(
    path: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> tuple[str, bool]:
    """Produce a unified diff with formatting-only hunk annotations.

    Returns (diff_text, is_formatting_only).
    """
    old_lines = (old_content or "").splitlines(keepends=True)
    new_lines = (new_content or "").splitlines(keepends=True)

    diff_lines, all_formatting = annotate_formatting_hunks(
        old_lines, new_lines, _hunk_is_formatting_only
    )

    if not diff_lines:
        return "", True  # no diff at all

    diff_text = "".join(diff_lines)
    return diff_text, all_formatting


# Local Variables:
# eval: (blacken-mode)
# End:
