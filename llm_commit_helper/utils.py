"""Utility functions: subprocess, size parsing, glob matching, git root."""

import fnmatch
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


COMMAND_TIMEOUT = 30  # seconds


def run_command(
    args: list[str],
    cwd: Optional[Path] = None,
    check: bool = False,
) -> tuple[int, str, str]:
    """Run a subprocess command and return (returncode, stdout, stderr).

    Never raises on non-zero exit unless check=True.
    Always enforces a 30-second timeout.
    """
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"[llm-commit-helper] Timeout running: {' '.join(args)}", file=sys.stderr)
        return 1, "", "timeout"
    except FileNotFoundError:
        return 1, "", f"command not found: {args[0]}"


def parse_size(value: str | int | float) -> int:
    """Parse a human-readable size string into bytes.

    Accepts: 200MB, 20KB, 4096, 1.5GB, etc.
    Returns the size in bytes as an integer.
    """
    if isinstance(value, (int, float)):
        return int(value)

    s = str(value).strip().upper()
    suffixes = {
        "GB": 1024**3,
        "MB": 1024**2,
        "KB": 1024,
        "B": 1,
    }
    for suffix, multiplier in suffixes.items():
        if s.endswith(suffix):
            number = s[: -len(suffix)].strip()
            return int(float(number) * multiplier)
    return int(float(s))


def glob_match(pattern: str, path: str) -> bool:
    """Return True if path matches a glob pattern.

    Supports ** for directory wildcards via fnmatch with path normalization.
    """
    # Normalize separators
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")

    # Try direct match
    if fnmatch.fnmatch(path, pattern):
        return True

    # Try matching just the filename against the pattern
    filename = Path(path).name
    if fnmatch.fnmatch(filename, pattern):
        return True

    # For ** patterns, check each path segment
    if "**" in pattern:
        parts = pattern.split("**")
        if len(parts) == 2:
            prefix, suffix = parts
            prefix = prefix.rstrip("/")
            suffix = suffix.lstrip("/")
            if prefix and not path.startswith(prefix):
                return False
            if suffix and not fnmatch.fnmatch(path, f"*{suffix}"):
                return False
            if prefix or suffix:
                return True

    return False


def find_git_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start (or cwd) to find the git repository root."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def make_temp_file(suffix: str = "", content: str = "") -> Path:
    """Create a named temp file with the given content, return its Path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        import os

        os.close(fd)
        raise
    return Path(path)


# Local Variables:
# eval: (blacken-mode)
# End:
