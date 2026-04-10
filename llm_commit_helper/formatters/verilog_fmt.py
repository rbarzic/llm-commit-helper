"""Verilog formatter: delete AUTO-generated sections before diffing."""

import re
import sys
from typing import Optional

from llm_commit_helper.utils import make_temp_file, run_command
from llm_commit_helper.diff_engine import annotate_formatting_hunks
from llm_commit_helper.formatters.generic_fmt import _hunk_is_formatting_only


# Regex for AUTO* macro keywords
AUTO_PATTERN = re.compile(
    r"\b(AUTOARG|AUTOINPUT|AUTOOUTPUT|AUTOINOUT|AUTOINSTPARAM|AUTOINST"
    r"|AUTOWIRE|AUTOREG|AUTOREGINPUT|AUTOLOGIC|AUTOASCIIENUM|AUTOSENSE"
    r"|AUTOUNUSED|AUTOTEMPLATE|AUTO_LISP)\b"
)


def _has_auto_macros(content: str) -> bool:
    """Return True if content uses any AUTO* Verilog macros."""
    return bool(AUTO_PATTERN.search(content))


def _run_emacs_delete_auto(file_path: str) -> bool:
    """Delete all AUTO-generated sections from file using emacs verilog-batch-delete-auto.

    This strips the expanded output (AUTOWIRE, AUTOINST, etc.) so that only
    the hand-written source remains, making diffs independent of AUTO ordering.
    Returns True on success.
    """
    rc, _, err = run_command(
        [
            "emacs",
            "--batch",
            file_path,
            "-f",
            "verilog-batch-delete-auto",
            "-f",
            "save-buffer",
        ]
    )
    return rc == 0


def format_verilog_diff(
    path: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> tuple[str, bool]:
    """Format Verilog diff by deleting AUTO-generated sections before comparing.

    verilog-batch-delete-auto removes all AUTO-expanded blocks (AUTOWIRE,
    AUTOINST, etc.), leaving only hand-written source. Diffing the stripped
    versions avoids spurious ordering differences in generated code.

    Returns (diff_text, is_formatting_only).
    Falls back to generic if emacs is not available or no AUTO* macros found.
    """
    combined = (old_content or "") + (new_content or "")
    has_auto = _has_auto_macros(combined)

    old_tmp = None
    new_tmp = None
    try:
        ext = ".sv" if path.endswith(".sv") else ".v"
        old_tmp = make_temp_file(suffix=ext, content=old_content or "")
        new_tmp = make_temp_file(suffix=ext, content=new_content or "")

        if has_auto:
            old_ok = _run_emacs_delete_auto(str(old_tmp))
            new_ok = _run_emacs_delete_auto(str(new_tmp))

            if not old_ok or not new_ok:
                print(
                    f"[llm-commit-helper] emacs not available or failed for {path}, falling back to generic",
                    file=sys.stderr,
                )
                from llm_commit_helper.formatters.generic_fmt import format_generic_diff

                return format_generic_diff(path, old_content, new_content)

            old_processed = old_tmp.read_text(encoding="utf-8")
            new_processed = new_tmp.read_text(encoding="utf-8")
        else:
            old_processed = old_content or ""
            new_processed = new_content or ""

        old_lines = old_processed.splitlines(keepends=True)
        new_lines = new_processed.splitlines(keepends=True)

        diff_lines, all_formatting = annotate_formatting_hunks(
            old_lines, new_lines, _hunk_is_formatting_only
        )

        if not diff_lines:
            if has_auto:
                return "[all changes are AUTO-generated - no user code changes]", True
            return "", True

        diff_text = "".join(diff_lines)
        if has_auto and all_formatting:
            diff_text = f"[formatting-only after AUTO deletion]\n{diff_text}"

        return diff_text, all_formatting

    finally:
        if old_tmp and old_tmp.exists():
            old_tmp.unlink()
        if new_tmp and new_tmp.exists():
            new_tmp.unlink()


# Local Variables:
# eval: (blacken-mode)
# End:
