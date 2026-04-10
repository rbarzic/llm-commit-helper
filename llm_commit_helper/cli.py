"""CLI entry point: argparse + main pipeline orchestration."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from llm_commit_helper.config import load_config, Config
from llm_commit_helper.git_staged import (
    get_staged_files,
    classify_file,
    load_file_contents,
    FileKind,
    FileStatus,
)
from llm_commit_helper.submodule import get_submodule_log, format_submodule_section
from llm_commit_helper.formatters import format_diff
from llm_commit_helper.output import OutputBuilder, format_file_header
from llm_commit_helper.utils import find_git_root


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="llm-commit-helper",
        description="LLM-friendly replacement for git diff --staged",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to config.jsonc (overrides hierarchy search)",
    )
    parser.add_argument(
        "--max-total-size",
        metavar="SIZE",
        help="Override max_total_size from config (e.g. 500, 20KB)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print extra diagnostic info to stderr",
    )
    return parser.parse_args(argv)


def _make_summary_header(
    files: list,
    config: Config,
    config_source: Optional[Path],
) -> str:
    counts: dict[str, int] = {
        "modified": 0,
        "added": 0,
        "deleted": 0,
        "excluded": 0,
        "too_large": 0,
        "submodule": 0,
        "binary": 0,
    }
    for f in files:
        kind_name = f.kind.value if f.kind else "modified"
        if kind_name in counts:
            counts[kind_name] += 1

    total = len(files)
    parts = []
    for k, v in counts.items():
        if v > 0:
            parts.append(f"{v} {k}")

    summary_line = f"Files: {total} total ({', '.join(parts)})"
    cfg_line = f"Config: {config_source}" if config_source else "Config: defaults"

    return f"=== Staged Changes Summary ===\n{summary_line}\n{cfg_line}\n\n"


def _process_file(f, config: Config, git_root: Path, verbose: bool) -> tuple[str, str]:
    """Process one staged file and return (header, body) strings."""
    kind = f.kind

    if kind == FileKind.EXCLUDED:
        header = format_file_header(f.path, "excluded")
        body = "[changed - excluded by rule]\n\n"
        return header, body

    if kind == FileKind.TOO_LARGE:
        header = format_file_header(f.path, "too_large")
        body = "[changed - file too large]\n\n"
        return header, body

    if kind == FileKind.BINARY:
        header = format_file_header(f.path, "binary")
        body = "[binary file changed]\n\n"
        return header, body

    if kind == FileKind.ADDED:
        header = format_file_header(f.path, "added")
        body = "[new file - contents not shown]\n\n"
        return header, body

    if kind == FileKind.DELETED:
        header = format_file_header(f.path, "deleted")
        body = "[file deleted]\n\n"
        return header, body

    if kind == FileKind.MODIFIED:
        f = load_file_contents(f, git_root)

        if f.old_content is None and f.new_content is None:
            header = format_file_header(f.path, "modified")
            body = "[could not retrieve file content]\n\n"
            return header, body

        diff_text, is_fmt_only = format_diff(f.path, f.old_content, f.new_content)

        if is_fmt_only and not diff_text:
            header = format_file_header(f.path, "modified", "formatting-only")
            body = "[no logic changes - formatting only]\n\n"
            return header, body

        if is_fmt_only:
            header = format_file_header(f.path, "modified", "formatting-only")
        else:
            header = format_file_header(f.path, "modified")

        body = (diff_text or "[empty diff]") + "\n\n"
        return header, body

    # Submodule handled separately
    return "", ""


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    git_root = find_git_root()
    if git_root is None:
        print("[llm-commit-helper] Error: not inside a git repository", file=sys.stderr)
        return 1

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path, start=git_root)

    # Apply CLI override for max_total_size
    if args.max_total_size:
        from llm_commit_helper.utils import parse_size

        config = Config(
            exclude_patterns=config.exclude_patterns,
            max_file_size=config.max_file_size,
            max_total_size=parse_size(args.max_total_size),
            source=config.source,
        )

    if args.verbose:
        print(
            f"[llm-commit-helper] git root: {git_root}",
            file=sys.stderr,
        )
        print(
            f"[llm-commit-helper] config: {config.source or 'defaults'}",
            file=sys.stderr,
        )
        print(
            f"[llm-commit-helper] max_total_size: {config.max_total_size}",
            file=sys.stderr,
        )

    # Get and classify staged files
    staged = get_staged_files(git_root)
    if not staged:
        print("No staged changes.", file=sys.stderr)
        return 0

    for f in staged:
        f.kind = classify_file(f, config, git_root)

    header = _make_summary_header(staged, config, config.source)
    builder = OutputBuilder(config.max_total_size)

    # Process regular files
    for f in staged:
        if f.kind == FileKind.SUBMODULE:
            continue  # handle submodules after

        file_header, file_body = _process_file(f, config, git_root, args.verbose)
        section = file_header + file_body
        if not builder.add_section(section, file_path=f.path):
            if args.verbose:
                print(
                    f"[llm-commit-helper] Budget exceeded, truncating at {f.path}",
                    file=sys.stderr,
                )

    # Process submodules
    for f in staged:
        if f.kind != FileKind.SUBMODULE:
            continue

        log_lines = get_submodule_log(f.path, f.old_hash, f.new_hash, git_root)
        section = format_submodule_section(f.path, f.old_hash, f.new_hash, log_lines) + "\n\n"
        builder.add_section(section, file_path=f.path)

    output = builder.build(
        header=header,
        footer_template="\n=== End of Staged Changes ({total_chars} chars) ===\n",
    )
    print(output)
    return 0


# Local Variables:
# eval: (blacken-mode)
# End:
