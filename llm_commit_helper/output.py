"""Output assembly: size-budgeted output builder."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FileSummary:
    path: str
    label: str          # e.g. "modified", "added", "excluded", ...
    content: str        # the body text for this file section
    truncated: bool = False


class OutputBuilder:
    """Assembles output sections while respecting max_total_size budget."""

    def __init__(self, max_total_size: int) -> None:
        self._max = max_total_size
        self._sections: list[str] = []
        self._current_size: int = 0
        self._truncated: bool = False
        self._truncated_files: list[str] = []

    def _remaining(self) -> int:
        return self._max - self._current_size

    def add_section(self, text: str, file_path: Optional[str] = None) -> bool:
        """Add a text section. Returns True if added in full, False if budget exceeded."""
        if self._truncated:
            if file_path:
                self._truncated_files.append(file_path)
            return False

        size = len(text)
        if self._current_size + size > self._max:
            self._truncated = True
            if file_path:
                self._truncated_files.append(file_path)
            return False

        self._sections.append(text)
        self._current_size += size
        return True

    def build(self, header: str, footer_template: str) -> str:
        """Build the final output string."""
        parts = [header]
        parts.extend(self._sections)

        if self._truncated:
            parts.append("\n[OUTPUT TRUNCATED - budget exceeded]\n")
            if self._truncated_files:
                parts.append("Remaining files (not shown):\n")
                for p in self._truncated_files:
                    parts.append(f"  {p}\n")

        total_chars = sum(len(p) for p in parts)
        footer = footer_template.format(total_chars=total_chars)
        parts.append(footer)
        return "".join(parts)

    @property
    def is_truncated(self) -> bool:
        return self._truncated

    @property
    def current_size(self) -> int:
        return self._current_size


def format_file_header(path: str, label: str, extra: str = "") -> str:
    """Format a file section header line."""
    parts = [f"--- File: {path} [{label}]"]
    if extra:
        parts.append(f" [{extra}]")
    parts.append(" ---\n")
    return "".join(parts)


# Local Variables:
# eval: (blacken-mode)
# End:
