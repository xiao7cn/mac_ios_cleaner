"""Delete scanned junk files safely."""

import os
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .scanner import ScanResult

ProgressCallback = Callable[[int, int, str], None]  # (current, total, path)

HOME = str(Path.home())


def _needs_sudo(path: Path) -> bool:
    return not str(path).startswith(HOME)


def _sudo_rm(path: Path) -> None:
    subprocess.run(
        ["sudo", "rm", "-rf", str(path)],
        check=True,
        capture_output=True,
    )


@dataclass
class CleanResult:
    category_key: str
    freed_bytes: int = 0
    deleted_count: int = 0
    failed: list[str] = field(default_factory=list)
    sudo_used: bool = False


def clean(
    scan_result: ScanResult,
    dry_run: bool = False,
    on_progress: ProgressCallback | None = None,
    use_sudo: bool = False,
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
            if use_sudo and _needs_sudo(entry.path) and not dry_run:
                try:
                    _sudo_rm(entry.path)
                    result.freed_bytes += entry.size
                    result.deleted_count += 1
                    result.sudo_used = True
                except subprocess.CalledProcessError:
                    result.failed.append(f"sudo 删除失败: {entry.path}")
            else:
                result.failed.append(f"权限不足: {entry.path} (用 --sudo 提权)")
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
