"""应用入口 — 创建 QApplication 和主窗口"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.config_manager import ConfigManager


def run():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("AI Studio")
    app.setOrganizationName("AI-Studio")

    # 加载配置
    config = ConfigManager()
    config.load()

    # 创建主窗口（延迟导入，确保 QApplication 已创建）
    from src.ui.main_window import MainWindow
    window = MainWindow(config)
    window.show()

    return app.exec()
