"""Delete scanned junk files safely."""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .scanner import ScanResult


@dataclass
class CleanResult:
    category_key: str
    freed_bytes: int = 0
    deleted_count: int = 0
    failed: list[str] = field(default_factory=list)


def clean(scan_result: ScanResult, dry_run: bool = False) -> CleanResult:
    result = CleanResult(category_key=scan_result.category_key)

    for entry in scan_result.files:
        try:
            if not dry_run:
                if entry.path.is_dir():
                    shutil.rmtree(entry.path)
                else:
                    entry.path.unlink()
            result.freed_bytes += entry.size
            result.deleted_count += 1
        except PermissionError:
            result.failed.append(f"权限不足: {entry.path}")
        except FileNotFoundError:
            pass
        except OSError as e:
            result.failed.append(f"删除失败 {entry.path}: {e}")

    _remove_empty_dirs(scan_result, dry_run)
    return result


def _remove_empty_dirs(scan_result: ScanResult, dry_run: bool) -> None:
    """Clean up empty parent directories left behind after file deletion."""
    if dry_run:
        return

    dirs_seen: set[Path] = set()
    for entry in scan_result.files:
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
