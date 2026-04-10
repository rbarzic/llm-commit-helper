"""Git interaction: staged file listing, classification, content retrieval."""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from llm_commit_helper.config import Config
from llm_commit_helper.utils import find_git_root, glob_match, run_command


class FileStatus(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class FileKind(Enum):
    EXCLUDED = "excluded"        # matched exclude rule or too large
    TOO_LARGE = "too_large"      # file size exceeds max_file_size
    ADDED = "added"              # new file - don't show content
    DELETED = "deleted"          # deleted file
    SUBMODULE = "submodule"      # gitlink / submodule
    MODIFIED = "modified"        # regular diff
    BINARY = "binary"            # binary file


@dataclass
class StagedFile:
    path: str                        # relative to git root
    status: FileStatus
    is_submodule: bool = False
    old_hash: Optional[str] = None   # for submodules: previous commit
    new_hash: Optional[str] = None   # for submodules: new commit
    kind: Optional[FileKind] = None  # set by classify_file()
    old_content: Optional[str] = None
    new_content: Optional[str] = None


def _parse_name_status(output: str) -> list[tuple[str, str, Optional[str]]]:
    """Parse git diff --name-status output into (status_char, path, old_path) tuples."""
    results = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status_char = parts[0][0]  # A, M, D, R, C, etc.
        if status_char in ("R", "C") and len(parts) >= 3:
            # Renamed: R100\told_path\tnew_path
            results.append((status_char, parts[2], parts[1]))
        elif len(parts) >= 2:
            results.append((status_char, parts[1], None))
    return results


def _get_submodule_hashes(git_root: Path) -> dict[str, tuple[str, str]]:
    """Return {path: (old_hash, new_hash)} for staged submodule changes."""
    rc, out, err = run_command(
        ["git", "diff", "--staged", "--raw"],
        cwd=git_root,
    )
    hashes: dict[str, tuple[str, str]] = {}
    if rc != 0:
        return hashes

    for line in out.splitlines():
        # Format: :old_mode new_mode old_hash new_hash status\tpath
        if not line.startswith(":"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        meta = parts[0].split()
        if len(meta) < 5:
            continue
        old_mode, new_mode, old_hash, new_hash, status = meta[0], meta[1], meta[2], meta[3], meta[4]
        path = parts[1]
        # Submodule mode is 160000
        if old_mode == ":160000" or new_mode == "160000" or old_mode == "160000":
            hashes[path] = (old_hash, new_hash)
        # Also check via the leading : format
        old_mode_clean = old_mode.lstrip(":")
        if old_mode_clean == "160000" or new_mode == "160000":
            hashes[path] = (old_hash, new_hash)

    return hashes


def _get_submodule_set(git_root: Path) -> set[str]:
    """Return the set of all submodule paths registered in .gitmodules."""
    rc, out, _ = run_command(
        ["git", "config", "--file", ".gitmodules", "--get-regexp", "path"],
        cwd=git_root,
    )
    paths = set()
    if rc != 0:
        return paths
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            paths.add(parts[1])
    return paths


def get_staged_files(git_root: Optional[Path] = None) -> list[StagedFile]:
    """Return StagedFile list for all currently staged changes."""
    if git_root is None:
        git_root = find_git_root()
    if git_root is None:
        print("[llm-commit-helper] Error: not inside a git repository", file=sys.stderr)
        return []

    rc, out, err = run_command(
        ["git", "diff", "--staged", "--name-status"],
        cwd=git_root,
    )
    if rc != 0:
        print(f"[llm-commit-helper] git diff failed: {err}", file=sys.stderr)
        return []

    parsed = _parse_name_status(out)
    submodule_paths = _get_submodule_set(git_root)
    submodule_hashes = _get_submodule_hashes(git_root)

    status_map = {
        "A": FileStatus.ADDED,
        "M": FileStatus.MODIFIED,
        "D": FileStatus.DELETED,
        "R": FileStatus.RENAMED,
        "C": FileStatus.MODIFIED,
    }

    files = []
    for status_char, path, old_path in parsed:
        status = status_map.get(status_char, FileStatus.MODIFIED)
        is_sub = path in submodule_paths
        old_h, new_h = submodule_hashes.get(path, (None, None))
        files.append(
            StagedFile(
                path=path,
                status=status,
                is_submodule=is_sub,
                old_hash=old_h,
                new_hash=new_h,
            )
        )

    return files


def _file_size_in_index(path: str, git_root: Path) -> int:
    """Return the size (bytes) of the staged version of a file, or 0 on error."""
    rc, out, _ = run_command(
        ["git", "cat-file", "-s", f":0:{path}"],
        cwd=git_root,
    )
    if rc != 0:
        return 0
    try:
        return int(out.strip())
    except ValueError:
        return 0


def _is_binary(path: str, git_root: Path) -> bool:
    """Heuristic: check if the staged file is binary."""
    rc, out, _ = run_command(
        ["git", "diff", "--staged", "--numstat", "--", path],
        cwd=git_root,
    )
    if rc == 0 and out.startswith("-\t-"):
        return True
    return False


def classify_file(f: StagedFile, config: Config, git_root: Path) -> FileKind:
    """Assign a FileKind to a StagedFile based on config rules."""
    # Submodule takes priority
    if f.is_submodule:
        return FileKind.SUBMODULE

    # Exclude patterns
    for pattern in config.exclude_patterns:
        if glob_match(pattern, f.path):
            return FileKind.EXCLUDED

    # Added files — no content shown
    if f.status == FileStatus.ADDED:
        return FileKind.ADDED

    # Deleted files
    if f.status == FileStatus.DELETED:
        return FileKind.DELETED

    # Size check (staged version)
    size = _file_size_in_index(f.path, git_root)
    if size > config.max_file_size:
        return FileKind.TOO_LARGE

    # Binary check
    if _is_binary(f.path, git_root):
        return FileKind.BINARY

    return FileKind.MODIFIED


def get_file_content(path: str, git_root: Path, staged: bool = True) -> Optional[str]:
    """Retrieve file content from git: staged (index) or committed (HEAD)."""
    if staged:
        ref = f":0:{path}"
    else:
        ref = f"HEAD:{path}"

    rc, out, err = run_command(["git", "show", ref], cwd=git_root)
    if rc != 0:
        return None
    return out


def load_file_contents(f: StagedFile, git_root: Path) -> StagedFile:
    """Load old and new content into StagedFile for MODIFIED/DELETED files."""
    if f.kind not in (FileKind.MODIFIED, FileKind.DELETED):
        return f

    old = get_file_content(f.path, git_root, staged=False)
    new = get_file_content(f.path, git_root, staged=True) if f.kind == FileKind.MODIFIED else None

    return StagedFile(
        path=f.path,
        status=f.status,
        is_submodule=f.is_submodule,
        old_hash=f.old_hash,
        new_hash=f.new_hash,
        kind=f.kind,
        old_content=old,
        new_content=new,
    )


# Local Variables:
# eval: (blacken-mode)
# End:
