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


def scan_category(category: Category) -> ScanResult:
    result = ScanResult(category_key=category.key)
    for sp in category.scan_paths:
        files, errors = scan_path(sp)
        result.files.extend(files)
        result.errors.extend(errors)
    return result
