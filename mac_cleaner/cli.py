"""Interactive CLI for mac_cleaner."""

import sys
import argparse
import subprocess
import threading
import time
from itertools import cycle

from . import __version__
from .categories import CATEGORIES, get_category, list_category_keys
from .scanner import scan_category, ScanResult
from .cleaner import clean, sudo_preflight
from .utils import (
    format_size,
    colored,
    bold,
    dim,
    risk_label,
    terminal_width,
    progress_bar,
)

BANNER = r"""
  __  __              ____ _
 |  \/  | __ _  ___  / ___| | ___  __ _ _ __   ___ _ __
 | |\/| |/ _` |/ __|| |   | |/ _ \/ _` | '_ \ / _ \ '__|
 | |  | | (_| | (__ | |___| |  __/ (_| | | | |  __/ |
 |_|  |_|\__,_|\___| \____|_|\___|\__,_|_| |_|\___|_|
"""


class Spinner:
    """Minimal terminal spinner."""

    def __init__(self, message: str = ""):
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Spinner":
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def _spin(self) -> None:
        frames = cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
        while not self._stop.is_set():
            sys.stdout.write(f"\r  {next(frames)} {self._message}")
            sys.stdout.flush()
            time.sleep(0.08)

    def stop(self, final: str = "") -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write(f"\r  {final}\n")
        sys.stdout.flush()


def _print_header() -> None:
    print(colored(BANNER, "cyan"))
    print(
        f"  {bold('Mac Cleaner')} {dim(f'v{__version__}')}  —  "
        f"macOS 磁盘垃圾清理工具\n"
    )


def _scan_all(
    keys: list[str] | None = None,
) -> dict[str, ScanResult]:
    targets = keys or list_category_keys()
    results: dict[str, ScanResult] = {}
    total = len(targets)

    for i, key in enumerate(targets, 1):
        cat = get_category(key)
        if cat is None:
            continue
        spinner = Spinner(f"正在扫描: {cat.icon}  {cat.name} ...").start()
        result = scan_category(cat)
        spinner.stop(
            f"✓ {cat.icon}  {cat.name}  "
            f"{colored(format_size(result.total_size), 'yellow')}  "
            f"({result.file_count} 个文件)  "
            f"{progress_bar(i, total, 20)}"
        )
        if result.total_size > 0:
            results[key] = result
    return results


def _print_summary(results: dict[str, ScanResult]) -> int:
    width = terminal_width()
    print("\n" + "─" * width)
    print(bold("  📊  扫描结果汇总\n"))

    grand_total = 0
    rows: list[tuple[str, str, str, str, int]] = []

    for key, result in sorted(
        results.items(), key=lambda x: x[1].total_size, reverse=True
    ):
        cat = get_category(key)
        if cat is None:
            continue
        size = result.total_size
        grand_total += size
        rows.append(
            (
                cat.icon,
                cat.name,
                format_size(size),
                risk_label(cat.risk.value),
                result.file_count,
            )
        )

    if not rows:
        print("  🎉  你的 Mac 非常干净，没有找到明显的垃圾文件！\n")
        return 0

    name_w = max(len(r[1]) for r in rows) + 2
    for icon, name, size, risk, count in rows:
        print(
            f"  {icon}  {name:<{name_w}} "
            f"{colored(size.rjust(10), 'yellow')}  "
            f"{str(count).rjust(6)} 个文件  {risk}"
        )

    print("─" * width)
    print(
        f"  {'🧹'} {bold('总计可清理:'):<{name_w + 2}} "
        f"{colored(format_size(grand_total).rjust(10), 'green')}"
    )
    print("─" * width)
    return grand_total


def _pick_categories(results: dict[str, ScanResult]) -> list[str]:
    keys = list(results.keys())
    print(f"\n  {bold('选择要清理的分类')}")
    print(f"  {dim('输入编号 (逗号分隔), a=全选, q=退出')}\n")

    for i, key in enumerate(keys, 1):
        cat = get_category(key)
        if cat is None:
            continue
        r = results[key]
        print(
            f"    {colored(str(i), 'cyan'):>6}.  {cat.icon}  {cat.name}  "
            f"({format_size(r.total_size)})"
        )

    print()
    answer = input("  ➜  ").strip().lower()
    if answer in ("q", "quit", "exit", ""):
        return []
    if answer == "a":
        return keys

    selected: list[str] = []
    for part in answer.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(keys):
                selected.append(keys[idx])
    return selected


def _confirm_clean(selected: list[str], results: dict[str, ScanResult]) -> bool:
    total = sum(results[k].total_size for k in selected if k in results)
    cats = ", ".join(
        get_category(k).name for k in selected if get_category(k) is not None
    )
    print(
        f"\n  ⚠️  即将清理: {colored(cats, 'yellow')}"
        f"\n  ⚠️  预计释放: {colored(format_size(total), 'green')}"
    )
    high_risk = [
        k
        for k in selected
        if get_category(k) is not None and get_category(k).risk.value == "high"
    ]
    if high_risk:
        names = ", ".join(
            get_category(k).name for k in high_risk if get_category(k) is not None
        )
        print(f"  {colored('⚠️  高风险分类: ' + names, 'red')}")

    answer = input(f"\n  确认清理？ {dim('[y/N]')} ").strip().lower()
    return answer in ("y", "yes")


def _make_progress_printer(cat_name: str, cat_icon: str):
    """Return a callback that prints live progress on a single line."""
    def on_progress(current: int, total: int, path: str) -> None:
        name = path.rsplit("/", 1)[-1]
        if len(name) > 40:
            name = name[:37] + "..."
        line = (
            f"  ⏳ {cat_icon}  {cat_name}  "
            f"{progress_bar(current, total, 20)}  "
            f"{current}/{total}  "
            f"{dim(name)}"
        )
        sys.stdout.write(f"\r\033[K{line}")
        sys.stdout.flush()
    return on_progress


def _do_clean(
    selected: list[str],
    results: dict[str, ScanResult],
    dry_run: bool = False,
    use_sudo: bool = False,
) -> None:
    if dry_run:
        print(f"\n  {colored('[DRY RUN]', 'magenta')} 仅模拟，不会删除任何文件\n")

    if use_sudo and not dry_run:
        try:
            sudo_preflight()
        except (subprocess.CalledProcessError, KeyboardInterrupt):
            print(f"  {colored('✗', 'red')} sudo 认证失败，将跳过系统级文件\n")
            use_sudo = False

    total_freed = 0
    for key in selected:
        if key not in results:
            continue
        cat = get_category(key)
        if cat is None:
            continue
        progress_cb = _make_progress_printer(cat.name, cat.icon)
        cr = clean(results[key], dry_run=dry_run, on_progress=progress_cb,
                    use_sudo=use_sudo)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        print(
            f"  ✓ {cat.icon}  {cat.name}  "
            f"释放 {colored(format_size(cr.freed_bytes), 'green')}  "
            f"({cr.deleted_count} 个文件/目录已删除)"
        )
        total_freed += cr.freed_bytes
        for msg in cr.messages:
            print(f"    {colored('ℹ', 'cyan')} {msg}")
        if cr.failed:
            for msg in cr.failed[:5]:
                print(f"    {colored('⚠', 'yellow')} {msg}")
            if len(cr.failed) > 5:
                print(f"    {dim(f'...还有 {len(cr.failed) - 5} 个错误')}")

    verb = "可释放" if dry_run else "已释放"
    print(f"\n  🎉  总计{verb}: {colored(format_size(total_freed), 'green')}\n")


def _cmd_scan(args: argparse.Namespace) -> None:
    _print_header()
    keys = args.categories.split(",") if args.categories else None
    sudo = getattr(args, "sudo", False)

    results = _scan_all(keys)
    grand_total = _print_summary(results)
    if grand_total == 0 or args.scan_only:
        return

    while results:
        selected = _pick_categories(results)
        if not selected:
            print("  退出。\n")
            return

        if args.dry_run:
            _do_clean(selected, results, dry_run=True, use_sudo=sudo)
        elif _confirm_clean(selected, results):
            _do_clean(selected, results, dry_run=False, use_sudo=sudo)
            for k in selected:
                results.pop(k, None)
        else:
            print("  跳过。\n")

        if not results:
            break

        print(f"  {dim('─' * 60)}")
        remaining = sum(r.total_size for r in results.values())
        print(
            f"\n  📋  还有 {bold(str(len(results)))} 个分类可清理，"
            f"共 {colored(format_size(remaining), 'yellow')}\n"
        )
        again = input(f"  继续选择其它分类？ {dim('[Y/n]')} ").strip().lower()
        if again in ("n", "no"):
            print("  退出。\n")
            return


def _cmd_list(args: argparse.Namespace) -> None:
    _print_header()
    print(bold("  支持的清理分类:\n"))
    for cat in CATEGORIES:
        print(
            f"  {cat.icon}  {cat.name:<16} "
            f"{risk_label(cat.risk.value)}  "
            f"{dim(cat.description)}"
        )
    print()


def _cmd_quick(args: argparse.Namespace) -> None:
    """Quick clean: only low-risk categories, auto-confirm."""
    _print_header()
    low_risk_keys = [c.key for c in CATEGORIES if c.risk.value == "low"]
    results = _scan_all(low_risk_keys)
    grand_total = _print_summary(results)
    if grand_total == 0:
        return

    selected = list(results.keys())
    sudo = getattr(args, "sudo", False)
    if args.dry_run:
        _do_clean(selected, results, dry_run=True, use_sudo=sudo)
        return

    if _confirm_clean(selected, results):
        _do_clean(selected, results, dry_run=False, use_sudo=sudo)
    else:
        print("  取消操作。\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mac-cleaner",
        description="Mac Cleaner — macOS 磁盘垃圾清理工具",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    # scan (default)
    p_scan = sub.add_parser("scan", help="扫描并交互式清理垃圾文件")
    p_scan.add_argument("-c", "--categories", help="只扫描指定分类 (逗号分隔)")
    p_scan.add_argument(
        "-n", "--dry-run", action="store_true", help="模拟运行，不删除文件"
    )
    p_scan.add_argument(
        "-s", "--scan-only", action="store_true", help="只扫描不清理"
    )
    p_scan.add_argument(
        "--no-sudo", dest="sudo", action="store_false",
        help="禁用 sudo 提权（默认对系统级路径自动 sudo）"
    )
    p_scan.set_defaults(func=_cmd_scan, sudo=True)

    # list
    p_list = sub.add_parser("list", help="列出所有支持的清理分类")
    p_list.set_defaults(func=_cmd_list)

    # quick
    p_quick = sub.add_parser("quick", help="快速清理（仅低风险分类）")
    p_quick.add_argument(
        "-n", "--dry-run", action="store_true", help="模拟运行，不删除文件"
    )
    p_quick.add_argument(
        "--no-sudo", dest="sudo", action="store_false",
        help="禁用 sudo 提权（默认对系统级路径自动 sudo）"
    )
    p_quick.set_defaults(func=_cmd_quick, sudo=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        args.categories = None
        args.dry_run = False
        args.scan_only = False
        args.sudo = True
        _cmd_scan(args)
    else:
        args.func(args)
