"""Python formatter: use black to separate logic from formatting changes."""

import sys
from typing import Optional

from llm_commit_helper.utils import make_temp_file, run_command
from llm_commit_helper.diff_engine import annotate_formatting_hunks
from llm_commit_helper.formatters.generic_fmt import _hunk_is_formatting_only


def _run_black(path_str: str) -> bool:
    """Run black --quiet on the given file path. Return True on success."""
    rc, _, err = run_command(["black", "--quiet", path_str])
    if rc != 0:
        return False
    return True


def format_python_diff(
    path: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> tuple[str, bool]:
    """Format Python diff using black to isolate logic changes.

    Returns (diff_text, is_formatting_only).
    Falls back to generic diff if black is not available.
    """
    old_tmp = None
    new_tmp = None
    try:
        old_tmp = make_temp_file(suffix=".py", content=old_content or "")
        new_tmp = make_temp_file(suffix=".py", content=new_content or "")

        old_ok = _run_black(str(old_tmp))
        new_ok = _run_black(str(new_tmp))

        if not old_ok or not new_ok:
            print(
                f"[llm-commit-helper] black not available or failed for {path}, falling back to generic",
                file=sys.stderr,
            )
            from llm_commit_helper.formatters.generic_fmt import format_generic_diff

            return format_generic_diff(path, old_content, new_content)

        old_formatted = old_tmp.read_text(encoding="utf-8")
        new_formatted = new_tmp.read_text(encoding="utf-8")

        old_lines = old_formatted.splitlines(keepends=True)
        new_lines = new_formatted.splitlines(keepends=True)

        diff_lines, all_formatting = annotate_formatting_hunks(
            old_lines, new_lines, _hunk_is_formatting_only
        )

        if not diff_lines:
            return "", True  # identical after formatting

        # Check if logic diff is empty (formatted versions match)
        # If the only differences are in the raw diff (pre-formatting), it's formatting-only
        raw_old = (old_content or "").splitlines(keepends=True)
        raw_new = (new_content or "").splitlines(keepends=True)
        raw_diff_lines, _ = annotate_formatting_hunks(raw_old, raw_new, _hunk_is_formatting_only)

        if not diff_lines and raw_diff_lines:
            return "[all changes are formatting-only (black normalization)]", True

        diff_text = "".join(diff_lines)
        return diff_text, all_formatting

    finally:
        if old_tmp and old_tmp.exists():
            old_tmp.unlink()
        if new_tmp and new_tmp.exists():
            new_tmp.unlink()


# Local Variables:
# eval: (blacken-mode)
# End:
