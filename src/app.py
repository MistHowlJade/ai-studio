"""应用入口 — 创建 QApplication 和主窗口"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.config_manager import ConfigManager
from src.logger import get_logger, setup_crash_handler, log_startup_info


def run():
    # 初始化日志系统（最早）
    logger = get_logger()
    setup_crash_handler()
    log_startup_info()

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
    logger.info(f"配置已加载，主题: {config.get('general.theme', 'dark')}")

    # 创建主窗口（延迟导入，确保 QApplication 已创建）
    from src.ui.main_window import MainWindow
    window = MainWindow(config)
    window.show()
    logger.info("主窗口已显示")

    exit_code = app.exec()
    logger.info(f"AI Studio 退出 (code={exit_code})")
    return exit_code
