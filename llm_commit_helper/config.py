"""Configuration loading: JSONC parsing, hierarchical search, Config dataclass."""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from llm_commit_helper.utils import find_git_root, parse_size


DEFAULT_MAX_FILE_SIZE = parse_size("200MB")
DEFAULT_MAX_TOTAL_SIZE = 20000

CONFIG_FILENAME = "config.jsonc"
CONFIG_DIR_NAME = ".llm-commit-helper"
GLOBAL_CONFIG_DIR = Path.home() / ".config" / "llm-commit-helper"


@dataclass
class Config:
    exclude_patterns: list[str] = field(default_factory=list)
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    max_total_size: int = DEFAULT_MAX_TOTAL_SIZE
    source: Optional[Path] = None  # which file was loaded, None = defaults


def _strip_jsonc_comments(text: str) -> str:
    """Remove // line comments and trailing commas from JSONC text."""
    # Remove // comments (not inside strings)
    result = []
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            result.append(ch)
        elif ch == "/" and not in_string and i + 1 < len(text) and text[i + 1] == "/":
            # Skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            result.append(ch)
        i += 1

    stripped = "".join(result)

    # Remove trailing commas before } or ]
    stripped = re.sub(r",\s*([}\]])", r"\1", stripped)
    return stripped


def _parse_jsonc(text: str) -> dict:
    """Parse JSONC text into a Python dict."""
    clean = _strip_jsonc_comments(text)
    return json.loads(clean)


def _load_config_file(path: Path) -> Optional[Config]:
    """Load and validate a config file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = _parse_jsonc(raw)
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"[llm-commit-helper] Warning: failed to parse {path}: {e}",
            file=sys.stderr,
        )
        return None

    rules = data.get("rules", {})
    exclude = rules.get("exclude", [])
    max_file_size_raw = rules.get("max_file_size", DEFAULT_MAX_FILE_SIZE)
    max_total_size_raw = rules.get("max_total_size", DEFAULT_MAX_TOTAL_SIZE)

    return Config(
        exclude_patterns=list(exclude),
        max_file_size=parse_size(max_file_size_raw),
        max_total_size=parse_size(max_total_size_raw),
        source=path,
    )


def _candidate_paths(start: Optional[Path] = None) -> list[Path]:
    """Return config file candidates from cwd up to git root, then global."""
    current = (start or Path.cwd()).resolve()
    git_root = find_git_root(current)
    candidates: list[Path] = []

    # Walk from cwd up to git root (or filesystem root)
    for parent in [current, *current.parents]:
        candidates.append(parent / CONFIG_FILENAME)
        candidates.append(parent / CONFIG_DIR_NAME / CONFIG_FILENAME)
        if git_root and parent == git_root:
            break

    # Global config
    candidates.append(GLOBAL_CONFIG_DIR / CONFIG_FILENAME)
    return candidates


def load_config(
    config_path: Optional[Path] = None,
    start: Optional[Path] = None,
) -> Config:
    """Load configuration. If config_path given, use it. Otherwise search hierarchy."""
    if config_path is not None:
        cfg = _load_config_file(config_path)
        if cfg is None:
            print(
                f"[llm-commit-helper] Warning: config file not found: {config_path}",
                file=sys.stderr,
            )
            return Config()
        return cfg

    for candidate in _candidate_paths(start):
        cfg = _load_config_file(candidate)
        if cfg is not None:
            return cfg

    return Config()  # defaults


# Local Variables:
# eval: (blacken-mode)
# End:
