"""Delete scanned junk files safely."""

import os
import subprocess
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .scanner import ScanResult

ProgressCallback = Callable[[int, int, str], None]  # (current, total, path)

HOME = str(Path.home())

SIMCTL_RUNTIME_PARENTS = {
    "/Library/Developer/CoreSimulator/Volumes",
    "/Library/Developer/CoreSimulator/Images",
    "/Library/Developer/CoreSimulator/Profiles/Runtimes",
}


def _needs_sudo(path: Path) -> bool:
    return not str(path).startswith(HOME)


def _is_simulator_runtime(path: Path) -> bool:
    return str(path.parent) in SIMCTL_RUNTIME_PARENTS


def sudo_preflight() -> None:
    """Prompt for sudo password once upfront so later calls don't block."""
    print("  🔑 需要管理员权限来清理系统级文件，请输入密码：")
    subprocess.run(["sudo", "-v"], check=True)
    print()


def _sudo_rm(path: Path) -> None:
    subprocess.run(
        ["sudo", "rm", "-rf", str(path)],
        check=True,
        capture_output=True,
    )


def _delete_simulator_runtimes() -> tuple[bool, str]:
    """Delete all simulator runtimes via xcrun simctl."""
    try:
        r = subprocess.run(
            ["xcrun", "simctl", "runtime", "delete", "all"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0:
            return True, r.stdout.strip()
        return False, r.stderr.strip()
    except FileNotFoundError:
        return False, "xcrun 未找到，请确认已安装 Xcode Command Line Tools"
    except subprocess.TimeoutExpired:
        return False, "simctl runtime delete 超时"


@dataclass
class CleanResult:
    category_key: str
    freed_bytes: int = 0
    deleted_count: int = 0
    failed: list[str] = field(default_factory=list)
    sudo_used: bool = False
    messages: list[str] = field(default_factory=list)


def clean(
    scan_result: ScanResult,
    dry_run: bool = False,
    on_progress: ProgressCallback | None = None,
    use_sudo: bool = False,
) -> CleanResult:
    result = CleanResult(category_key=scan_result.category_key)
    total = len(scan_result.files)

    sim_runtime_entries = [e for e in scan_result.files if _is_simulator_runtime(e.path)]
    regular_entries = [e for e in scan_result.files if not _is_simulator_runtime(e.path)]

    if sim_runtime_entries and not dry_run:
        sim_size = sum(e.size for e in sim_runtime_entries)
        ok, msg = _delete_simulator_runtimes()
        if ok:
            result.freed_bytes += sim_size
            result.deleted_count += len(sim_runtime_entries)
            result.messages.append(f"通过 simctl 删除了 {len(sim_runtime_entries)} 个模拟器运行时")
        else:
            result.failed.append(f"simctl runtime delete: {msg}")
    elif sim_runtime_entries and dry_run:
        for e in sim_runtime_entries:
            result.freed_bytes += e.size
            result.deleted_count += 1

    for i, entry in enumerate(regular_entries, 1):
        if on_progress:
            on_progress(i, len(regular_entries), str(entry.path))
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
                except subprocess.CalledProcessError as e:
                    err = e.stderr.decode().strip() if e.stderr else "未知错误"
                    result.failed.append(f"sudo 失败 {entry.path}: {err}")
            else:
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
