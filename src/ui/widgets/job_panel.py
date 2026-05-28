"""任务面板 — 活跃任务列表 + 历史记录，支持多代理并行可视化"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QProgressBar, QSizePolicy,
)

from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, ProgressRing, FluentIcon,
    InfoBar, InfoBarPosition,
)

from src.jobs.job_manager import JobStatus


class JobCard(CardWidget):
    """单个任务卡片 — 显示代理、状态、进度"""

    cancelled = pyqtSignal(str)
    view_output = pyqtSignal(str)

    def __init__(self, job_data: dict, parent=None):
        super().__init__(parent)
        self.job_id = job_data["job_id"]
        self.setFixedHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # 第一行：代理图标 + prompt 摘要 + 状态
        topRow = QHBoxLayout()

        icons = {"opencode": "🤖", "hermes": "⚡", "openclaw": "🦞"}
        icon = icons.get(job_data.get("agent_name", ""), "🤖")

        self.agentLabel = StrongBodyLabel(
            f"{icon} {job_data.get('agent_name', '').title()}"
        )
        topRow.addWidget(self.agentLabel)

        self.promptLabel = BodyLabel(
            job_data.get("prompt", "")[:50]
        )
        self.promptLabel.setStyleSheet("color: #a6adc8;")
        topRow.addWidget(self.promptLabel, 1)

        # 状态指示灯
        status = job_data.get("status", "pending")
        status_config = {
            "pending": ("⏳ 排队中", "#f9e2af"),
            "running": ("🟢 运行中", "#a6e3a1"),
            "completed": ("✅ 完成", "#a6e3a1"),
            "failed": ("❌ 失败", "#f38ba8"),
            "cancelled": ("⏹ 已取消", "#a6adc8"),
        }
        status_text, status_color = status_config.get(
            status, (status, "#cdd6f4")
        )
        self.statusLabel = BodyLabel(status_text)
        self.statusLabel.setStyleSheet(f"color: {status_color};")
        topRow.addWidget(self.statusLabel)

        layout.addLayout(topRow)

        # 第二行：模型 + 耗时 + 操作
        infoRow = QHBoxLayout()

        model_text = f"模型: {job_data.get('model', '默认')}"
        modelLabel = CaptionLabel(model_text)
        modelLabel.setStyleSheet("color: #585b70;")
        infoRow.addWidget(modelLabel)

        infoRow.addStretch()

        duration = job_data.get("duration", "")
        if duration:
            durLabel = CaptionLabel(f"耗时: {duration}")
            durLabel.setStyleSheet("color: #585b70;")
            infoRow.addWidget(durLabel)

        infoRow.addSpacing(8)

        # 操作按钮
        if status == "running" or status == "pending":
            cancelBtn = PushButton("取消")
            cancelBtn.setFixedWidth(50)
            cancelBtn.clicked.connect(
                lambda: self.cancelled.emit(self.job_id)
            )
            infoRow.addWidget(cancelBtn)

        if status in ("completed", "failed"):
            viewBtn = PushButton("查看")
            viewBtn.setFixedWidth(50)
            viewBtn.clicked.connect(
                lambda: self.view_output.emit(self.job_id)
            )
            infoRow.addWidget(viewBtn)

        layout.addLayout(infoRow)

        # 进度条（仅 running 状态）
        if status == "running":
            self.progressBar = QProgressBar()
            self.progressBar.setRange(0, 0)  # 不确定进度
            self.progressBar.setFixedHeight(4)
            self.progressBar.setTextVisible(False)
            self.progressBar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #313244;
                    border-radius: 2px;
                }
                QProgressBar::chunk {
                    background-color: #89b4fa;
                    border-radius: 2px;
                }
            """)
            layout.addWidget(self.progressBar)


class JobPanel(QScrollArea):
    """任务面板 — 活跃任务 + 历史记录"""

    job_cancel = pyqtSignal(str)
    job_view = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.container = QWidget(self)
        self.setWidget(self.container)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        # 标题
        self.titleLabel = StrongBodyLabel("📋 任务队列")
        self.layout.addWidget(self.titleLabel)

        # 统计栏
        self.statsLabel = CaptionLabel("")
        self.statsLabel.setStyleSheet("color: #585b70;")
        self.layout.addWidget(self.statsLabel)

        # 任务卡片容器
        self.cardsLayout = QVBoxLayout()
        self.cardsLayout.setSpacing(8)
        self.layout.addLayout(self.cardsLayout)

        self.layout.addStretch()

        self._cards: dict[str, JobCard] = {}

    def add_or_update_job(self, job_data: dict):
        """添加或更新任务卡片"""
        job_id = job_data["job_id"]

        if job_id in self._cards:
            # 移除旧卡片
            old = self._cards.pop(job_id)
            self.cardsLayout.removeWidget(old)
            old.deleteLater()

        # 创建新卡片
        card = JobCard(job_data, self.container)
        card.cancelled.connect(self.job_cancel)
        card.view_output.connect(self.job_view)

        # 按状态排序：running > pending > 其他
        status_order = {
            "running": 0, "pending": 1,
            "completed": 2, "failed": 2, "cancelled": 2
        }
        order = status_order.get(job_data.get("status", ""), 3)

        # 找到插入位置
        insert_idx = 0
        for i in range(self.cardsLayout.count()):
            item = self.cardsLayout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, "job_id"):
                    existing_order = status_order.get(
                        self._get_card_status(w), 3
                    )
                    if order < existing_order:
                        break
            insert_idx = i + 1

        self.cardsLayout.insertWidget(insert_idx, card)
        self._cards[job_id] = card

        self._update_stats()

    def remove_job(self, job_id: str):
        """移除任务卡片"""
        if job_id in self._cards:
            card = self._cards.pop(job_id)
            self.cardsLayout.removeWidget(card)
            card.deleteLater()
            self._update_stats()

    def clear_completed(self):
        """清除已完成的任务卡片"""
        to_remove = []
        for job_id, card in self._cards.items():
            status = self._get_card_status(card)
            if status in ("completed", "failed", "cancelled"):
                to_remove.append(job_id)
        for jid in to_remove:
            self.remove_job(jid)

    def set_jobs(self, jobs: list[dict]):
        """批量设置任务列表"""
        # 清除旧卡片
        for card in list(self._cards.values()):
            self.cardsLayout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # 添加新卡片
        for job_data in jobs:
            self.add_or_update_job(job_data)

    def _get_card_status(self, card: JobCard) -> str:
        """从卡片获取状态"""
        text = card.statusLabel.text()
        if "排队" in text:
            return "pending"
        if "运行" in text:
            return "running"
        if "完成" in text:
            return "completed"
        if "失败" in text:
            return "failed"
        if "取消" in text:
            return "cancelled"
        return "unknown"

    def _update_stats(self):
        """更新统计栏"""
        counts = {"running": 0, "pending": 0, "completed": 0}
        for card in self._cards.values():
            s = self._get_card_status(card)
            if s in counts:
                counts[s] += 1

        parts = []
        if counts["running"]:
            parts.append(f"🟢 {counts['running']} 运行中")
        if counts["pending"]:
            parts.append(f"⏳ {counts['pending']} 排队中")
        if counts["completed"]:
            parts.append(f"✅ {counts['completed']} 已完成")

        self.statsLabel.setText(" · ".join(parts) if parts else "暂无任务")
