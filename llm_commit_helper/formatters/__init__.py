"""Formatter dispatcher: selects the right formatter by file extension."""

from pathlib import Path
from typing import Optional


def format_diff(
    path: str,
    old_content: Optional[str],
    new_content: Optional[str],
) -> tuple[str, bool]:
    """Format a diff for the given file path.

    Returns (diff_text, is_formatting_only).
    is_formatting_only=True means no logic changes were found.
    """
    ext = Path(path).suffix.lower()

    if ext == ".py":
        from llm_commit_helper.formatters.python_fmt import format_python_diff

        return format_python_diff(path, old_content, new_content)
    elif ext in (".v", ".sv"):
        from llm_commit_helper.formatters.verilog_fmt import format_verilog_diff

        return format_verilog_diff(path, old_content, new_content)
    else:
        from llm_commit_helper.formatters.generic_fmt import format_generic_diff

        return format_generic_diff(path, old_content, new_content)


# Local Variables:
# eval: (blacken-mode)
# End:
