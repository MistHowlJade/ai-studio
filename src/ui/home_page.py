"""首页 Dashboard — 实时状态轮询 + 任务面板 + 对话线程历史"""
import shutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (
    ScrollArea, CardWidget, TitleLabel, SubtitleLabel,
    StrongBodyLabel, BodyLabel, PrimaryPushButton, PushButton,
    FluentIcon, InfoBar, InfoBarPosition,
)

from src.ui.widgets.job_panel import JobPanel


class StatusCard(CardWidget):
    """代理状态卡片"""

    def __init__(self, icon, title, status, status_color, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        iconLabel = QLabel(icon)
        iconLabel.setStyleSheet("font-size: 28px;")
        layout.addWidget(iconLabel)

        titleLabel = StrongBodyLabel(title, self)
        layout.addWidget(titleLabel)

        statusLabel = BodyLabel(status, self)
        statusLabel.setStyleSheet(f"color: {status_color};")
        layout.addWidget(statusLabel)

        layout.addStretch()
        self.statusLabel = statusLabel

    def update_status(self, status, color):
        self.statusLabel.setText(status)
        self.statusLabel.setStyleSheet(f"color: {color};")


class HomePage(ScrollArea):
    """首页 Dashboard — 实时状态 + 任务 + 历史"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("homePage")
        self._session_store = None

        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(24)

        # 标题
        title = TitleLabel("AI Studio", self.view)
        layout.addWidget(title)

        subtitle = SubtitleLabel("通用 AI 桌面平台 — 编程代理 & 创意生成", self.view)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # ── 代理状态卡片行 ──
        cardsTitle = StrongBodyLabel("🤖 AI 代理", self.view)
        layout.addWidget(cardsTitle)

        cardsLayout = QHBoxLayout()
        cardsLayout.setSpacing(16)

        # OpenCode
        self.opencodeCard = StatusCard(
            "🤖", "OpenCode", "检测中...", "#a6adc8", self.view
        )
        btn = PrimaryPushButton("使用 →", self.opencodeCard)
        btn.clicked.connect(lambda: self._navigate_to("opencodePage"))
        self.opencodeCard.layout().addWidget(btn)
        cardsLayout.addWidget(self.opencodeCard)

        # Hermes
        self.hermesCard = StatusCard(
            "⚡", "Hermes", "检测中...", "#a6adc8", self.view
        )
        btn = PrimaryPushButton("使用 →", self.hermesCard)
        btn.clicked.connect(lambda: self._navigate_to("hermesPage"))
        self.hermesCard.layout().addWidget(btn)
        cardsLayout.addWidget(self.hermesCard)

        # OpenClaw
        self.openclawCard = StatusCard(
            "🦞", "OpenClaw", "检测中...", "#a6adc8", self.view
        )
        btn = PrimaryPushButton("使用 →", self.openclawCard)
        btn.clicked.connect(lambda: self._navigate_to("openclawPage"))
        self.openclawCard.layout().addWidget(btn)
        cardsLayout.addWidget(self.openclawCard)

        cardsLayout.addStretch()
        layout.addLayout(cardsLayout)

        # ── ComfyUI 状态 ──
        layout.addSpacing(8)
        comfyTitle = StrongBodyLabel("🎨 创意工坊", self.view)
        layout.addWidget(comfyTitle)

        comfyRow = QHBoxLayout()
        self.comfyuiCard = StatusCard(
            "🎨", "ComfyUI", "检测中...", "#a6adc8", self.view
        )
        self.comfyuiCard.setFixedSize(300, 100)
        btn = PrimaryPushButton("打开工坊 →", self.comfyuiCard)
        btn.clicked.connect(lambda: self._navigate_to("comfyuiPage"))
        self.comfyuiCard.layout().addWidget(btn)
        comfyRow.addWidget(self.comfyuiCard)
        comfyRow.addStretch()
        layout.addLayout(comfyRow)

        # ── 活跃任务面板 ──
        layout.addSpacing(16)
        self.jobPanel = JobPanel(self.view)
        self.jobPanel.job_cancel.connect(self._on_job_cancel)
        self.jobPanel.job_view.connect(self._on_job_view)
        self.jobPanel.setMaximumHeight(300)
        layout.addWidget(self.jobPanel)

        # ── 最近对话 ──
        layout.addSpacing(8)
        recentsTitle = StrongBodyLabel("📝 最近对话", self.view)
        layout.addWidget(recentsTitle)

        self.recentsLabel = BodyLabel("暂无对话记录", self.view)
        self.recentsLabel.setStyleSheet("color: #585b70;")
        layout.addWidget(self.recentsLabel)

        layout.addStretch()

        # ── 定时轮询代理可用性 ──
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_availability)
        self._poll_timer.start(10000)  # 每 10 秒
        self._poll_availability()      # 立即执行一次

    # ── 诊断 ──

    def set_diagnostics(self, diagnostics):
        """应用启动诊断结果到状态卡片"""
        agents = diagnostics["agents"]
        card_map = {
            "opencode": self.opencodeCard,
            "hermes": self.hermesCard,
            "openclaw": self.openclawCard,
        }

        for name, dep in agents.items():
            card = card_map.get(name)
            if not card:
                continue
            enabled = self.config.get(f"agents.{name}.enabled", True)
            if not enabled:
                card.update_status("⏸ 已禁用", "#a6adc8")
            elif dep.available:
                card.update_status(f"✅ 就绪 ({dep.version})", "#a6e3a1")
            else:
                card.update_status(f"❌ {dep.error}", "#f38ba8")

        # ComfyUI
        comfy_cli = diagnostics["comfy_cli"]
        comfy_srv = diagnostics["comfyui_server"]
        if comfy_srv.available:
            self.comfyuiCard.update_status("🟢 服务运行中", "#a6e3a1")
        elif comfy_cli.available:
            self.comfyuiCard.update_status("⚪ CLI 已安装", "#a6adc8")
        else:
            self.comfyuiCard.update_status("⚠️ 未安装", "#f9e2af")

        # 停止轮询（启动诊断已做初始检测）
        # 后续轮询继续更新运行时状态

    # ── 轮询 ──

    def _poll_availability(self):
        """轮询代理 CLI 可用性"""
        agents = {
            "opencode": ("opencode", self.opencodeCard),
            "hermes": ("hermes", self.hermesCard),
            "openclaw": ("openclaw", self.openclawCard),
        }

        for agent_name, (binary, card) in agents.items():
            available = shutil.which(binary) is not None
            enabled = self.config.get(f"agents.{agent_name}.enabled", True)

            if not enabled:
                card.update_status("⏸ 已禁用", "#a6adc8")
            elif available:
                card.update_status("✅ 就绪", "#a6e3a1")
            else:
                card.update_status("❌ 未安装", "#f38ba8")

        # ComfyUI
        comfy_available = shutil.which("comfy") is not None
        if comfy_available:
            self.comfyuiCard.update_status("✅ CLI 可用", "#a6e3a1")
        else:
            self.comfyuiCard.update_status("❌ 未安装", "#f38ba8")

    def _poll_threads(self):
        """更新最近对话"""
        if self._session_store is None:
            return
        sessions = self._session_store.get_recent(limit=5)
        if not sessions:
            self.recentsLabel.setText("暂无对话记录")
            return
        text = "\n".join(
            f"📌 [{s['agent'].title()}] {s.get('title', s['prompt'][:40])} — {s['time']}"
            for s in sessions
        )
        self.recentsLabel.setText(text)

    # ── 设置引用 ──

    def set_session_store(self, store):
        """绑定会话存储"""
        self._session_store = store
        self._poll_threads()

    def set_job_manager(self, manager):
        """绑定任务管理器"""
        self._job_manager = manager
        manager.job_submitted.connect(self._on_job_update)
        manager.job_started.connect(self._on_job_update)
        manager.job_finished.connect(self._on_job_update)
        manager.job_progress.connect(
            lambda jid, data: self.jobPanel.add_or_update_job(data)
        )

    # ── 导航 ──

    def _navigate_to(self, page_name):
        window = self.window()
        if hasattr(window, page_name):
            page = getattr(window, page_name)
            window.stackedWidget.setCurrentWidget(page)
            route_keys = {
                "opencodePage": "opencodePage",
                "hermesPage": "hermesPage",
                "openclawPage": "openclawPage",
                "comfyuiPage": "comfyuiPage",
            }
            if page_name in route_keys:
                window.navigationInterface.setCurrentItem(
                    route_keys[page_name]
                )

    # ── 任务回调 ──

    def _on_job_update(self, job_id):
        """任务状态更新"""
        if hasattr(self, "_job_manager"):
            job = self._job_manager.get_job(job_id)
            if job:
                data = {
                    "job_id": job.job_id,
                    "agent_name": job.agent_name,
                    "prompt": job.prompt[:80],
                    "model": job.model or "默认",
                    "status": job.status.value,
                    "exit_code": job.exit_code,
                    "error_message": job.error_message,
                    "duration": job.duration_str,
                    "output_lines": len(job.output_lines),
                    "created_at": job.created_at,
                }
                self.jobPanel.add_or_update_job(data)

    def _on_job_cancel(self, job_id):
        if hasattr(self, "_job_manager"):
            self._job_manager.cancel(job_id)

    def _on_job_view(self, job_id):
        """查看任务输出 — 导航到对应代理页面"""
        if not hasattr(self, "_job_manager"):
            return
        job = self._job_manager.get_job(job_id)
        if not job:
            return

        # 导航到对应代理页面
        page_map = {
            "opencode": "opencodePage",
            "hermes": "hermesPage",
            "openclaw": "openclawPage",
        }
        page_name = page_map.get(job.agent_name)
        if page_name:
            self._navigate_to(page_name)

    # ── 兼容旧 API ──

    def update_agent_status(self, agent_name, available, message=""):
        card_map = {
            "opencode": self.opencodeCard,
            "hermes": self.hermesCard,
            "openclaw": self.openclawCard,
            "comfyui": self.comfyuiCard,
        }
        card = card_map.get(agent_name)
        if card:
            if available:
                card.update_status(message or "✅ 就绪", "#a6e3a1")
            else:
                card.update_status(message or "❌ 不可用", "#f38ba8")

    def update_recents(self, sessions):
        if not sessions:
            self.recentsLabel.setText("暂无对话记录")
            return
        text = "\n".join(
            f"📌 {s['agent']}: {s['prompt'][:40]}...  — {s['time']}"
            for s in sessions[:5]
        )
        self.recentsLabel.setText(text)
