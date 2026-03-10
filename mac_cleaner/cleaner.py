"""Delete scanned junk files safely."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .scanner import ScanResult

ProgressCallback = Callable[[int, int, str], None]  # (current, total, path)


@dataclass
class CleanResult:
    category_key: str
    freed_bytes: int = 0
    deleted_count: int = 0
    failed: list[str] = field(default_factory=list)


def clean(
    scan_result: ScanResult,
    dry_run: bool = False,
    on_progress: ProgressCallback | None = None,
) -> CleanResult:
    result = CleanResult(category_key=scan_result.category_key)
    total = len(scan_result.files)

    for i, entry in enumerate(scan_result.files, 1):
        if on_progress:
            on_progress(i, total, str(entry.path))
        try:
            if not dry_run:
                if entry.is_bulk or entry.path.is_dir():
                    shutil.rmtree(entry.path, ignore_errors=False)
                else:
                    entry.path.unlink()
            result.freed_bytes += entry.size
            result.deleted_count += 1
        except PermissionError:
            result.failed.append(f"权限不足: {entry.path}")
        except FileNotFoundError:
            result.deleted_count += 1
        except OSError as e:
            result.failed.append(f"删除失败 {entry.path}: {e}")

    if not dry_run:
        _remove_empty_dirs(scan_result)
    return result


def _remove_empty_dirs(scan_result: ScanResult) -> None:
    """Clean up empty parent directories left behind after file deletion."""
    dirs_seen: set[Path] = set()
    for entry in scan_result.files:
        if entry.is_bulk:
            continue
        parent = entry.path.parent
        while parent != parent.parent:
            if parent in dirs_seen:
                break
            dirs_seen.add(parent)
            parent = parent.parent

    for d in sorted(dirs_seen, key=lambda p: len(p.parts), reverse=True):
        try:
            if d.exists() and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass
