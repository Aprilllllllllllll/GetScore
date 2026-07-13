#!/usr/bin/env bash
# ============================================
# 初始化环境 — 安装 uv 和项目依赖
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================"
echo "  成绩查询系统 — 环境初始化"
echo "========================================"
echo ""

# ---- 检查 Python ----
echo "[1/3] 检查 Python 环境..."
if command -v python &> /dev/null && python --version 2>&1 | grep -q "Python"; then
    PYTHON=python
elif command -v python3 &> /dev/null && python3 --version 2>&1 | grep -q "Python"; then
    PYTHON=python3
else
    echo "错误: 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1)
echo "  ✓ $PYTHON_VERSION"
echo ""

# ---- 安装 uv ----
echo "[2/3] 检查/安装 uv 包管理器..."
if command -v uv &> /dev/null; then
    echo "  ✓ uv 已安装: $(uv --version)"
else
    echo "  正在安装 uv..."
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex" 2>/dev/null || {
        # 备选：pip 安装
        echo "  PowerShell 安装失败，尝试通过 pip 安装..."
        pip install uv
    }
    # 刷新 PATH（Windows Git Bash 兼容）
    export PATH="$HOME/.cargo/bin:$PATH"
    if command -v uv &> /dev/null; then
        echo "  ✓ uv 安装成功"
    else
        echo "  警告: uv 安装后未找到命令，尝试使用 pip 作为备选..."
    fi
fi
echo ""

# ---- 安装依赖 ----
echo "[3/3] 安装项目依赖..."
cd "$PROJECT_ROOT"

if command -v uv &> /dev/null; then
    # 使用 uv 管理依赖
    uv venv 2>/dev/null || true
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    uv sync
    echo "  ✓ 依赖安装完成"
else
    # 备选：pip 直接安装
    echo "  使用 pip 安装依赖..."
    pip install -r <(cat pyproject.toml | grep -A10 'dependencies' | grep -o '"[^"]*"' | tr -d '"' | sed 's/^/pip install /' | bash -s) 2>/dev/null || {
        pip install requests pycryptodome apscheduler python-dotenv
    }
    echo "  ✓ 依赖安装完成（pip 模式）"
fi
echo ""

# ---- 检查 .env 文件 ----
echo "----------------------------------------"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "✓ .env 文件已存在"
else
    echo "! .env 文件不存在，请复制 .env.example 并填入真实信息："
    echo "  cp .env.example .env"
    echo "  然后编辑 .env 填入学号和密码"
fi
echo "========================================"
