"""Utility helpers for display and formatting."""

import shutil
from datetime import datetime


def format_size(size_bytes: int) -> str:
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_index]}"


def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def terminal_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def colored(text: str, color: str) -> str:
    """Simple ANSI coloring without external deps."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    prefix = colors.get(color, "")
    reset = colors["reset"]
    return f"{prefix}{text}{reset}"


def bold(text: str) -> str:
    return colored(text, "bold")


def dim(text: str) -> str:
    return colored(text, "dim")


RISK_COLORS = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
}


def risk_label(risk_value: str) -> str:
    labels = {"low": "安全", "medium": "中等", "high": "谨慎"}
    label = labels.get(risk_value, risk_value)
    color = RISK_COLORS.get(risk_value, "white")
    return colored(f"[{label}]", color)


def progress_bar(current: int, total: int, width: int = 30) -> str:
    if total == 0:
        return ""
    pct = current / total
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {pct:.0%}"
