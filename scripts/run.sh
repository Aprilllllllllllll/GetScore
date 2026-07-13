#!/usr/bin/env bash
# ============================================
# 单次成绩查询 — 查询一次并推送通知
# ============================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件！"
    echo "请执行: cp .env.example .env"
    echo "然后编辑 .env 填入真实学号和密码"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi

echo "正在查询成绩..."
python main.py once --semester 2025-2026-2
