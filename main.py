#!/usr/bin/env python3
"""AI Studio — 通用 AI 桌面平台入口"""
import sys
import os

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import run

if __name__ == "__main__":
    sys.exit(run())
