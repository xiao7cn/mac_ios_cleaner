#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
MIN_PYTHON="3.10"

find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            local major minor req_major req_minor
            major=${ver%%.*}; minor=${ver#*.}
            req_major=${MIN_PYTHON%%.*}; req_minor=${MIN_PYTHON#*.}
            if (( major > req_major || (major == req_major && minor >= req_minor) )); then
                echo "$cmd"; return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || { echo "错误: 需要 Python >= $MIN_PYTHON"; exit 1; }

if [ ! -d "$VENV_DIR" ]; then
    echo "⏳ 首次运行，创建虚拟环境..."
    "$PYTHON" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"
    echo "✅ 环境就绪"
fi

exec "$VENV_DIR/bin/mac-cleaner" "$@"
