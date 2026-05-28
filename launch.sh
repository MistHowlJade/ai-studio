#!/bin/bash
# AI Studio 启动脚本
# 用法: bash launch.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -f ".venv/bin/python3" ]; then
    echo "❌ 虚拟环境未安装，请先运行: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# 启动 GUI 应用
echo "🚀 启动 AI Studio..."
.venv/bin/python3 main.py
