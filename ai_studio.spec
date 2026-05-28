# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 — AI Studio 桌面应用"""
import os
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent

# ── 基础配置 ──

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # 工作流 JSON
        (str(ROOT / "src/media/workflows"), "src/media/workflows"),
        # README 等文档
        (str(ROOT / "README.md"), "."),
    ],
    hiddenimports=[
        # PyQt6 核心
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # QFluentWidgets 及资源
        "qfluentwidgets",
        "qfluentwidgets.window",
        "qfluentwidgets.components",
        "qfluentwidgets.common",
        "qfluentwidgets._rc",
        # 配置/数据
        "yaml",
        "requests",
        "websocket",
        "PIL",
        "sqlite3",
        "json",
        "uuid",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "torch",
        "tensorflow",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ── 过滤掉非必要的 Qt 组件减小体积 ──

a.datas = [
    d for d in a.datas
    if not any(x in d[0].lower() for x in [
        "qtwebengine", "qtwebchannel", "qtquick",
        "qt3d", "qtmultimedia", "qtsensors",
        "qtpositioning", "qtserialport", "qtbluetooth",
    ])
]

# ── 可执行文件 ──

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AI-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
