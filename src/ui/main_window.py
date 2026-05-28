"""主窗口 — FluentWindow 侧边栏导航 + 实时状态轮询"""
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    SplashScreen, SystemThemeListener, Theme, setTheme,
)

from src.ui.home_page import HomePage
from src.ui.agent_page import AgentPage
from src.ui.comfyui_page import ComfyUIPage
from src.ui.settings_page import SettingsPage
from src.jobs.job_manager import JobManager
from src.storage.session_store import SessionStore


class MainWindow(FluentWindow):
    """主窗口 — 侧边栏导航 + 全局状态"""

    def __init__(self, config):
        super().__init__()
        self.config = config

        # 全局服务
        self.jobManager = JobManager(max_concurrent=3)
        self.sessionStore = SessionStore()

        self._init_window()
        self._create_pages()
        self._init_navigation()
        self._inject_services()
        self._start_live_polling()

        # 系统主题监听
        self.themeListener = SystemThemeListener(self)
        self.themeListener.start()

        self.splashScreen.finish()

    def _init_window(self):
        self.resize(1200, 800)
        self.setMinimumWidth(900)
        self.setWindowTitle("AI Studio")

        theme = self.config.get("general.theme", "dark")
        if theme == "dark":
            setTheme(Theme.DARK)

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(80, 80))

        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        self.show()
        QApplication.processEvents()

    def _create_pages(self):
        self.homePage = HomePage(self.config, self)
        self.opencodePage = AgentPage(self.config, "opencode", self)
        self.hermesPage = AgentPage(self.config, "hermes", self)
        self.openclawPage = AgentPage(self.config, "openclaw", self)
        self.comfyuiPage = ComfyUIPage(self.config, self)
        self.settingsPage = SettingsPage(self.config, self)

    def _inject_services(self):
        """注入全局服务到各页面"""
        # HomePage 获得 JobManager + SessionStore
        self.homePage.set_job_manager(self.jobManager)
        self.homePage.set_session_store(self.sessionStore)

        # AgentPage 获得 JobManager + SessionStore
        for page in [self.opencodePage, self.hermesPage, self.openclawPage]:
            page.set_job_manager(self.jobManager)
            page.set_session_store(self.sessionStore)

    def _start_live_polling(self):
        """启动定时轮询"""
        # ComfyUI 状态轮询
        self._comfy_poll = QTimer(self)
        self._comfy_poll.timeout.connect(self._poll_comfyui)
        self._comfy_poll.start(15000)  # 每 15 秒

    def _poll_comfyui(self):
        """轮询 ComfyUI 状态"""
        import requests
        host = self.config.get("comfyui.host", "127.0.0.1")
        port = self.config.get("comfyui.port", 8188)
        try:
            r = requests.get(
                f"http://{host}:{port}/system_stats", timeout=2
            )
            if r.status_code == 200:
                self.homePage.comfyuiCard.update_status(
                    "🟢 运行中", "#a6e3a1"
                )
            else:
                self.homePage.comfyuiCard.update_status(
                    "⚪ 未运行", "#a6adc8"
                )
        except Exception:
            self.homePage.comfyuiCard.update_status(
                "⚪ 未运行", "#a6adc8"
            )

    def _init_navigation(self):
        pos = NavigationItemPosition.SCROLL

        self.addSubInterface(self.homePage, FluentIcon.HOME, "首页")
        self.navigationInterface.addSeparator()

        self.addSubInterface(
            self.opencodePage, FluentIcon.ROBOT, "OpenCode", pos
        )
        self.addSubInterface(
            self.hermesPage, FluentIcon.DEVELOPER_TOOLS, "Hermes", pos
        )
        self.addSubInterface(
            self.openclawPage, FluentIcon.COMMAND_PROMPT, "OpenClaw", pos
        )
        self.navigationInterface.addSeparator()

        self.addSubInterface(
            self.comfyuiPage, FluentIcon.PALETTE, "创意工坊", pos
        )

        self.addSubInterface(
            self.settingsPage, FluentIcon.SETTING, "设置",
            NavigationItemPosition.BOTTOM
        )

        self.navigationInterface.setAcrylicEnabled(True)

    def closeEvent(self, e):
        self._comfy_poll.stop()
        self.sessionStore.close()
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)
