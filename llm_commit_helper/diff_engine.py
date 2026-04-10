"""Diff engine: difflib wrapper with per-hunk formatting annotation."""

import difflib
from typing import Callable


def make_unified_diff(
    old_lines: list[str],
    new_lines: list[str],
    fromfile: str = "old",
    tofile: str = "new",
    n: int = 3,
) -> list[str]:
    """Produce unified diff lines (with headers) using difflib."""
    return list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=fromfile,
            tofile=tofile,
            n=n,
        )
    )


def _split_hunks(
    diff_lines: list[str],
) -> tuple[list[str], list[tuple[int, int]]]:
    """Split unified diff into header lines and list of (start, end) hunk spans."""
    hunk_spans: list[tuple[int, int]] = []
    hunk_start = None

    for i, line in enumerate(diff_lines):
        if line.startswith("@@"):
            if hunk_start is not None:
                hunk_spans.append((hunk_start, i))
            hunk_start = i

    if hunk_start is not None:
        hunk_spans.append((hunk_start, len(diff_lines)))

    return hunk_spans


def annotate_formatting_hunks(
    old_lines: list[str],
    new_lines: list[str],
    is_formatting_only: Callable[[list[str], list[str]], bool],
    n: int = 3,
) -> tuple[list[str], bool]:
    """Produce annotated unified diff lines.

    For each hunk that is formatting-only, inserts a [formatting-only] marker
    after the @@ line.

    Returns (diff_lines, all_hunks_are_formatting_only).
    """
    raw = make_unified_diff(old_lines, new_lines, n=n)
    if not raw:
        return [], True

    hunk_spans = _split_hunks(raw)
    if not hunk_spans:
        return raw, False

    result: list[str] = []
    all_formatting = True
    # Copy header lines (before first hunk)
    first_hunk_start = hunk_spans[0][0]
    result.extend(raw[:first_hunk_start])

    for start, end in hunk_spans:
        hunk_body = raw[start:end]
        removed = [l[1:] for l in hunk_body if l.startswith("-") and not l.startswith("---")]
        added = [l[1:] for l in hunk_body if l.startswith("+") and not l.startswith("+++")]

        fmt_only = is_formatting_only(removed, added)
        if not fmt_only:
            all_formatting = False

        result.append(hunk_body[0])  # the @@ line
        if fmt_only:
            result.append("[formatting-only]\n")
        result.extend(hunk_body[1:])

    return result, all_formatting


# Local Variables:
# eval: (blacken-mode)
# End:
