"""Scan filesystem for junk files by category."""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .categories import Category, ScanPath


@dataclass
class FileEntry:
    path: Path
    size: int
    mtime: float
    is_bulk: bool = False  # True = represents a whole directory tree


@dataclass
class ScanResult:
    category_key: str
    files: list[FileEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def file_count(self) -> int:
        return len(self.files)


PROTECTED_PATHS = {
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/private/var/db",
}


def _is_protected(path: Path) -> bool:
    s = str(path)
    return any(s.startswith(p) for p in PROTECTED_PATHS)


def _should_skip_file(path: Path) -> bool:
    return path.name == ".DS_Store" or path.name.startswith("._")


def _dir_size(path: Path) -> int:
    """Fast directory size via os.scandir (avoids Path overhead)."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += _dir_size(Path(entry.path))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def scan_path(sp: ScanPath) -> tuple[list[FileEntry], list[str]]:
    root = Path(sp.path)
    files: list[FileEntry] = []
    errors: list[str] = []

    if not root.exists():
        return files, errors

    if _is_protected(root):
        errors.append(f"跳过受保护路径: {root}")
        return files, errors

    now = time.time()
    min_age_seconds = sp.min_age_days * 86400

    if sp.bulk:
        return _scan_bulk(root, sp, now, min_age_seconds)

    try:
        if sp.glob == "**/*":
            iterator = root.rglob("*")
        elif sp.glob == "*":
            iterator = root.glob("*")
        else:
            iterator = root.glob(sp.glob)

        for p in iterator:
            try:
                if not p.is_file():
                    continue
                if _should_skip_file(p):
                    continue
                stat = p.stat()
                if min_age_seconds > 0 and (now - stat.st_mtime) < min_age_seconds:
                    continue
                files.append(FileEntry(path=p, size=stat.st_size, mtime=stat.st_mtime))
            except PermissionError:
                errors.append(f"权限不足: {p}")
            except OSError as e:
                errors.append(f"无法访问 {p}: {e}")
    except PermissionError:
        errors.append(f"权限不足: {root}")
    except OSError as e:
        errors.append(f"扫描错误 {root}: {e}")

    return files, errors


def _scan_bulk(
    root: Path, sp: ScanPath, now: float, min_age_seconds: float
) -> tuple[list[FileEntry], list[str]]:
    """Scan top-level children as whole units — much faster for huge trees."""
    files: list[FileEntry] = []
    errors: list[str] = []
    try:
        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue
            try:
                stat = child.stat()
                if min_age_seconds > 0 and (now - stat.st_mtime) < min_age_seconds:
                    continue
                if child.is_dir():
                    size = _dir_size(child)
                else:
                    size = stat.st_size
                files.append(FileEntry(
                    path=child, size=size, mtime=stat.st_mtime, is_bulk=True
                ))
            except PermissionError:
                errors.append(f"权限不足: {child}")
            except OSError as e:
                errors.append(f"无法访问 {child}: {e}")
    except PermissionError:
        errors.append(f"权限不足: {root}")
    except OSError as e:
        errors.append(f"扫描错误 {root}: {e}")
    return files, errors


def scan_category(category: Category) -> ScanResult:
    result = ScanResult(category_key=category.key)
    for sp in category.scan_paths:
        files, errors = scan_path(sp)
        result.files.extend(files)
        result.errors.extend(errors)
    return result
