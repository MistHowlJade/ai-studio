"""日志系统 — 文件日志、崩溃捕获、自动轮转"""
import logging
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 默认日志目录
LOG_DIR = Path.home() / ".ai-studio" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志格式
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logger = None


def get_logger(name: str = "ai-studio") -> logging.Logger:
    """获取日志器（单例）"""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    # 控制台输出（INFO 以上）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    _logger.addHandler(console)

    # 文件输出（DEBUG 以上，自动轮转）
    log_file = LOG_DIR / "ai-studio.log"
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=7,              # 保留 7 个备份
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    _logger.addHandler(file_handler)

    return _logger


def setup_crash_handler():
    """安装全局崩溃捕获器，未处理异常写入日志"""
    logger = get_logger()

    def _exception_hook(exc_type, exc_value, exc_tb):
        """全局异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 用户 Ctrl+C，正常退出
            logger.info("用户中断 (Ctrl+C)")
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_text = "".join(tb_lines)
        logger.critical(f"未捕获的异常:\n{tb_text}")

        # 写入单独的崩溃日志
        crash_file = LOG_DIR / f"crash-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write(f"=== AI Studio 崩溃报告 ===\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"平台: {sys.platform}\n\n")
            f.write(tb_text)

        # 调用原始处理器
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _exception_hook


def get_log_file_path() -> Path:
    """获取当前日志文件路径"""
    return LOG_DIR / "ai-studio.log"


def get_crash_reports() -> list[Path]:
    """获取所有崩溃报告"""
    return sorted(
        LOG_DIR.glob("crash-*.log"),
        key=os.path.getmtime,
        reverse=True,
    )


def log_startup_info():
    """记录启动信息"""
    logger = get_logger()
    logger.info("=" * 50)
    logger.info(f"AI Studio 启动")
    logger.info(f"Python: {sys.version}")
    logger.info(f"平台: {sys.platform}")
    logger.info(f"日志目录: {LOG_DIR}")
    logger.info("=" * 50)
