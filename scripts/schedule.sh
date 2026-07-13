#!/usr/bin/env bash
# ============================================
# 启动定时轮询 — 后台持续监控成绩变化
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

echo "========================================"
echo "  启动定时轮询模式"
echo "  日志文件: logs/app.log"
echo "  按 Ctrl+C 停止"
echo "========================================"
echo ""

python main.py schedule
