"""Junk file category definitions, modeled after CleanMyMac X."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


class Risk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ScanPath:
    path: str
    glob: str = "**/*"
    min_age_days: int = 0
    description: str = ""


@dataclass
class Category:
    key: str
    name: str
    icon: str
    description: str
    risk: Risk
    scan_paths: list[ScanPath] = field(default_factory=list)
    enabled: bool = True


HOME = str(Path.home())

CATEGORIES: list[Category] = [
    # ── System Junk ──────────────────────────────────────────
    Category(
        key="system_cache",
        name="系统缓存",
        icon="🗄️",
        description="macOS 和应用程序的缓存文件",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(f"{HOME}/Library/Caches", description="用户级缓存"),
            ScanPath("/Library/Caches", description="系统级缓存"),
        ],
    ),
    Category(
        key="system_logs",
        name="系统日志",
        icon="📋",
        description="系统和应用程序的日志文件",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(f"{HOME}/Library/Logs", description="用户日志"),
            ScanPath("/Library/Logs", description="系统日志"),
            ScanPath("/var/log", glob="*.log*", description="系统 var 日志"),
            ScanPath(
                f"{HOME}/Library/Containers",
                glob="**/Logs/**/*",
                description="容器化应用日志",
            ),
        ],
    ),
    Category(
        key="crash_reports",
        name="崩溃报告",
        icon="💥",
        description="应用程序崩溃产生的诊断报告",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Logs/DiagnosticReports",
                description="用户崩溃报告",
            ),
            ScanPath("/Library/Logs/DiagnosticReports", description="系统崩溃报告"),
        ],
    ),
    # ── Developer Junk ───────────────────────────────────────
    Category(
        key="xcode",
        name="Xcode 垃圾",
        icon="🔨",
        description="Xcode 构建缓存、旧版设备支持和归档",
        risk=Risk.MEDIUM,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Developer/Xcode/DerivedData",
                description="DerivedData 构建缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/Xcode/Archives",
                description="旧归档文件",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/Xcode/iOS DeviceSupport",
                description="iOS 设备支持文件",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/Xcode/watchOS DeviceSupport",
                description="watchOS 设备支持文件",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/Xcode/UserData/Previews",
                description="SwiftUI 预览缓存",
            ),
        ],
    ),
    Category(
        key="xcode_simulators",
        name="Xcode 模拟器",
        icon="📲",
        description="iOS/watchOS/tvOS 模拟器运行时、设备数据和缓存（可能占用数十 GB）",
        risk=Risk.HIGH,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Developer/CoreSimulator/Devices",
                description="模拟器设备数据",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/CoreSimulator/Caches",
                description="模拟器缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Developer/CoreSimulator/Temp",
                description="模拟器临时文件",
            ),
            ScanPath(
                "/Library/Developer/CoreSimulator/Volumes",
                description="模拟器运行时卷（cryptex）",
            ),
            ScanPath(
                "/Library/Developer/CoreSimulator/Images",
                description="模拟器运行时镜像",
            ),
            ScanPath(
                "/Library/Developer/CoreSimulator/Profiles/Runtimes",
                description="模拟器运行时配置",
            ),
        ],
    ),
    Category(
        key="homebrew",
        name="Homebrew 缓存",
        icon="🍺",
        description="Homebrew 下载的包缓存",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(f"{HOME}/Library/Caches/Homebrew", description="Homebrew 缓存"),
        ],
    ),
    Category(
        key="package_managers",
        name="包管理器缓存",
        icon="📦",
        description="npm / pip / yarn / conda / CocoaPods 等缓存",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(f"{HOME}/.npm/_cacache", description="npm 缓存"),
            ScanPath(f"{HOME}/Library/Caches/pip", description="pip 缓存"),
            ScanPath(f"{HOME}/Library/Caches/yarn", description="yarn 缓存"),
            ScanPath(f"{HOME}/.cache/pip", description="pip 缓存 (Linux 风格)"),
            ScanPath(f"{HOME}/.conda/pkgs", description="conda 包缓存"),
            ScanPath(
                f"{HOME}/Library/Caches/CocoaPods",
                description="CocoaPods 缓存",
            ),
            ScanPath(f"{HOME}/.gradle/caches", description="Gradle 缓存"),
            ScanPath(f"{HOME}/.m2/repository", description="Maven 本地仓库"),
            ScanPath(f"{HOME}/.cargo/registry/cache", description="Cargo 缓存"),
            ScanPath(f"{HOME}/go/pkg/mod/cache", description="Go module 缓存"),
        ],
    ),
    # ── Mail & Messages ──────────────────────────────────────
    Category(
        key="mail_attachments",
        name="邮件附件",
        icon="📎",
        description="Mail 应用下载的附件缓存",
        risk=Risk.MEDIUM,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Containers/com.apple.mail/Data/Library/Mail Downloads",
                description="Mail 附件下载",
            ),
        ],
    ),
    # ── iOS Backups ──────────────────────────────────────────
    Category(
        key="ios_backups",
        name="iOS 设备备份",
        icon="📱",
        description="iPhone / iPad 的本地备份（可能占用大量空间）",
        risk=Risk.HIGH,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Application Support/MobileSync/Backup",
                description="iOS 设备备份",
            ),
        ],
    ),
    # ── Trash ────────────────────────────────────────────────
    Category(
        key="trash",
        name="废纸篓",
        icon="🗑️",
        description="废纸篓中等待永久删除的文件",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(f"{HOME}/.Trash", description="用户废纸篓"),
        ],
    ),
    # ── Downloads ────────────────────────────────────────────
    Category(
        key="old_downloads",
        name="旧下载文件",
        icon="📥",
        description="下载文件夹中超过 90 天的文件",
        risk=Risk.HIGH,
        scan_paths=[
            ScanPath(
                f"{HOME}/Downloads",
                min_age_days=90,
                glob="*",
                description="90 天前的下载文件",
            ),
        ],
    ),
    # ── Browser Data ─────────────────────────────────────────
    Category(
        key="browser_cache",
        name="浏览器缓存",
        icon="🌐",
        description="Safari / Chrome / Firefox 等浏览器缓存",
        risk=Risk.LOW,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Caches/com.apple.Safari",
                description="Safari 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Caches/Google/Chrome",
                description="Chrome 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Caches/Firefox/Profiles",
                description="Firefox 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Caches/com.microsoft.edgemac",
                description="Edge 缓存",
            ),
        ],
    ),
    # ── Docker ───────────────────────────────────────────────
    Category(
        key="docker",
        name="Docker 数据",
        icon="🐳",
        description="Docker Desktop 的磁盘映像和缓存（需谨慎）",
        risk=Risk.HIGH,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Containers/com.docker.docker/Data",
                description="Docker Desktop 数据",
            ),
        ],
    ),
    # ── Application Support Caches ───────────────────────────
    Category(
        key="app_support_cache",
        name="应用支持缓存",
        icon="💾",
        description="各类应用在 Application Support 中的缓存数据",
        risk=Risk.MEDIUM,
        scan_paths=[
            ScanPath(
                f"{HOME}/Library/Application Support/Slack/Cache",
                description="Slack 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Application Support/discord/Cache",
                description="Discord 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Application Support/Code/Cache",
                description="VS Code 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Application Support/Code/CachedData",
                description="VS Code 缓存数据",
            ),
            ScanPath(
                f"{HOME}/Library/Application Support/Cursor/Cache",
                description="Cursor 缓存",
            ),
            ScanPath(
                f"{HOME}/Library/Application Support/Cursor/CachedData",
                description="Cursor 缓存数据",
            ),
        ],
    ),
]


def get_category(key: str) -> Category | None:
    for cat in CATEGORIES:
        if cat.key == key:
            return cat
    return None


def list_category_keys() -> list[str]:
    return [c.key for c in CATEGORIES]
