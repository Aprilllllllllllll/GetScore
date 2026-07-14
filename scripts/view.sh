#!/usr/bin/env bash
# ============================================
# 查看成绩 — 格式化展示本地已存储的成绩
# 可选参数会原样传递给 main.py，例如:
#   bash scripts/view.sh --semester 2025-2026-2
# ============================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 激活虚拟环境（如果存在）
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi

python main.py view "$@"
