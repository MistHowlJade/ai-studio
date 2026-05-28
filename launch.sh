#!/bin/bash
# AI Studio 启动脚本
# 用法: bash launch.sh
#
# 自动检测运行模式：
#   - PyInstaller 打包（单文件可执行）→ 直接运行
#   - 源码开发模式 → 使用 .venv 虚拟环境

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 检测是否在 PyInstaller 打包环境中 ──
if [ -n "$_MEIPASS2" ]; then
    # PyInstaller 环境 — 单文件可执行已经在 PATH 中
    echo "🚀 AI Studio (打包版)"
    exec "AI-Studio" "$@"
fi

# ── 源码开发模式 ──

# 检查虚拟环境
if [ ! -f ".venv/bin/python3" ]; then
    echo "❌ 虚拟环境未安装"
    echo "   请先运行: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "🚀 启动 AI Studio (开发模式)..."

# 写入启动日志
LOG_DIR="$HOME/.ai-studio/logs"
mkdir -p "$LOG_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动" >> "$LOG_DIR/launch.log"

.venv/bin/python3 main.py
