# Mac Cleaner 🧹

命令行版 macOS 磁盘垃圾清理工具，灵感来自 CleanMyMac X。

纯 Python 实现，无任何外部依赖，扫描并分类清理 macOS 上常见的垃圾文件。

## 功能特性

- **分类扫描** — 系统缓存、日志、崩溃报告、Xcode 垃圾、Homebrew/npm/pip 缓存、浏览器缓存、邮件附件、iOS 备份、废纸篓等 13 个分类
- **风险等级** — 每个分类标注安全/中等/谨慎等级，避免误删
- **交互式选择** — 扫描后自主选择要清理的分类
- **Dry Run 模式** — 先模拟再决定，安全可靠
- **快速清理** — 一键清理所有低风险分类
- **零依赖** — 仅使用 Python 标准库

## 清理分类

| 分类 | 风险 | 说明 |
|------|------|------|
| 🗄️ 系统缓存 | 安全 | macOS 和应用程序的缓存文件 |
| 📋 系统日志 | 安全 | 系统和应用程序的日志文件 |
| 💥 崩溃报告 | 安全 | 应用崩溃诊断报告 |
| 🔨 Xcode 垃圾 | 中等 | DerivedData、设备支持、归档、SwiftUI 预览缓存 |
| 📲 Xcode 模拟器 | 谨慎 | 模拟器运行时、设备数据和缓存（常占数十 GB） |
| 🍺 Homebrew 缓存 | 安全 | Homebrew 包缓存 |
| 📦 包管理器缓存 | 安全 | npm/pip/yarn/conda/CocoaPods/Gradle/Maven/Cargo/Go |
| 📎 邮件附件 | 中等 | Mail 下载的附件缓存 |
| 📱 iOS 设备备份 | 谨慎 | iPhone/iPad 本地备份 |
| 🗑️ 废纸篓 | 安全 | 废纸篓中的文件 |
| 📥 旧下载文件 | 谨慎 | 下载文件夹中超过 90 天的文件 |
| 🌐 浏览器缓存 | 安全 | Safari/Chrome/Firefox/Edge 缓存 |
| 🐳 Docker 数据 | 谨慎 | Docker Desktop 磁盘映像 |
| 💾 应用支持缓存 | 中等 | Slack/Discord/VS Code/Cursor 等缓存 |

## 安装

```bash
# 方式一：直接运行
python -m mac_cleaner

# 方式二：安装为命令行工具
pip install -e .
mac-cleaner
```

## 使用方法

### 完整扫描（交互式）

```bash
# 扫描所有分类，交互式选择清理
python -m mac_cleaner

# 或使用 scan 子命令
mac-cleaner scan
```

### 只扫描不清理

```bash
mac-cleaner scan -s
```

### 模拟运行（不删除文件）

```bash
mac-cleaner scan -n
```

### 指定分类扫描

```bash
mac-cleaner scan -c system_cache,system_logs,trash
```

### 快速清理（仅低风险）

```bash
mac-cleaner quick

# 配合 dry-run
mac-cleaner quick -n
```

### 查看所有分类

```bash
mac-cleaner list
```

## 系统要求

- macOS 10.15+
- Python 3.10+

## 安全说明

- 所有高风险操作会提前警告并要求确认
- 支持 `--dry-run` 模拟运行
- 不会触碰系统核心文件（`/System`、`/usr`、`/bin`等）
- 不需要 root 权限（仅清理用户级文件）

## License

MIT
