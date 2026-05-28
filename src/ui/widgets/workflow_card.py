"""工作流卡片组件 — ComfyUI 工作流选择和缩略图预览"""
import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy,
)

from qfluentwidgets import CardWidget, StrongBodyLabel, BodyLabel, ToolButton, FluentIcon


class WorkflowCard(CardWidget):
    """工作流卡片 — 缩略图 + 名称 + 类型标签 + 操作按钮

    信号：
        selected(dict): 工作流被选中时携带其元数据
        removed(str): 工作流被移除时携带其名称
    """

    selected = pyqtSignal(dict)
    removed = pyqtSignal(str)

    def __init__(
        self,
        name: str,
        description: str = "",
        wf_type: str = "image",
        thumbnail_path: str = None,
        metadata: dict = None,
        removable: bool = False,
        parent=None,
    ):
        """
        Args:
            name: 工作流名称
            description: 描述文本
            wf_type: 类型标签 ("image", "video", "audio")
            thumbnail_path: 缩略图路径
            metadata: 额外元数据
            removable: 是否可移除（自定义导入的）
        """
        super().__init__(parent)
        self.wf_name = name
        self.metadata = metadata or {}

        self.setFixedSize(200, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 类型图标 + 名称
        header = QHBoxLayout()

        type_icons = {
            "image": "🖼️", "video": "🎥", "audio": "🎵", "other": "📄"
        }
        icon = type_icons.get(wf_type, "📄")

        self.iconLabel = QLabel(icon)
        self.iconLabel.setStyleSheet("font-size: 20px;")
        header.addWidget(self.iconLabel)

        self.nameLabel = StrongBodyLabel(name[:20], self)
        self.nameLabel.setWordWrap(True)
        header.addWidget(self.nameLabel, 1)

        layout.addLayout(header)

        # 缩略图（占位）
        self.thumbLabel = QLabel(self)
        self.thumbLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbLabel.setFixedHeight(80)
        self.thumbLabel.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                color: #585b70;
            }
        """)

        if thumbnail_path and Path(thumbnail_path).exists():
            pixmap = QPixmap(thumbnail_path)
            scaled = pixmap.scaled(
                176, 80, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbLabel.setPixmap(scaled)
        else:
            # 占位符
            type_placeholders = {
                "image": "🖼️ 图片生成",
                "video": "🎬 视频生成",
                "audio": "🎵 音频生成",
                "other": "📄 工作流",
            }
            placeholder = type_placeholders.get(wf_type, "📄 工作流")
            self.thumbLabel.setText(placeholder)

        layout.addWidget(self.thumbLabel)

        # 描述
        if description:
            descLabel = BodyLabel(description[:40], self)
            descLabel.setStyleSheet("color: #585b70; font-size: 11px;")
            descLabel.setWordWrap(True)
            layout.addWidget(descLabel)

        # 底部：类型标签 + 操作按钮
        footer = QHBoxLayout()

        type_colors = {
            "image": ("#a6e3a1", "图片"),
            "video": ("#89b4fa", "视频"),
            "audio": ("#f9e2af", "音频"),
            "other": ("#a6adc8", "其他"),
        }
        color, label = type_colors.get(wf_type, ("#a6adc8", "其他"))

        self.typeBadge = QLabel(label)
        self.typeBadge.setStyleSheet(
            f"background-color: {color}22; color: {color}; "
            "padding: 2px 8px; border-radius: 4px; font-size: 10px;"
        )
        footer.addWidget(self.typeBadge)

        footer.addStretch()

        if removable:
            removeBtn = ToolButton(FluentIcon.DELETE, self)
            removeBtn.setFixedSize(20, 20)
            removeBtn.clicked.connect(
                lambda: self.removed.emit(self.wf_name)
            )
            footer.addWidget(removeBtn)

        layout.addLayout(footer)

        # 点击选中
        self.clicked = False

    def mousePressEvent(self, event):
        """点击发射 selected 信号"""
        self.selected.emit({
            "name": self.wf_name,
            "metadata": self.metadata,
        })
        super().mousePressEvent(event)

    def set_thumbnail(self, image_path):
        """动态更新缩略图"""
        if Path(image_path).exists():
            pixmap = QPixmap(image_path)
            scaled = pixmap.scaled(
                176, 80, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumbLabel.setPixmap(scaled)


class WorkflowGrid(QWidget):
    """工作流卡片网格布局"""

    workflow_selected = pyqtSignal(dict)
    workflow_removed = pyqtSignal(str)

    def __init__(self, parent=None, columns=3):
        super().__init__(parent)
        self.columns = columns
        self._cards = []

        self.layout = None  # QGridLayout，动态重建
        self._rebuild_layout()

    def add_workflow(
        self, name, description="", wf_type="image",
        thumbnail=None, metadata=None, removable=False
    ):
        """添加工作流卡片"""
        card = WorkflowCard(
            name=name, description=description, wf_type=wf_type,
            thumbnail_path=thumbnail, metadata=metadata,
            removable=removable, parent=self,
        )
        card.selected.connect(self.workflow_selected)
        card.removed.connect(self._on_removed)
        self._cards.append(card)
        self._rebuild_layout()

    def remove_workflow(self, name):
        """移除工作流"""
        for card in self._cards:
            if card.wf_name == name:
                self._cards.remove(card)
                card.deleteLater()
                break
        self._rebuild_layout()

    def clear(self):
        """清空所有工作流"""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self._rebuild_layout()

    def _on_removed(self, name):
        self.remove_workflow(name)
        self.workflow_removed.emit(name)

    def _rebuild_layout(self):
        """重建网格布局"""
        from PyQt6.QtWidgets import QGridLayout, QSizePolicy

        # 删除旧布局
        if self.layout:
            while self.layout.count():
                item = self.layout.takeAt(0)
            del self.layout

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        for i, card in enumerate(self._cards):
            row = i // self.columns
            col = i % self.columns
            self.layout.addWidget(card, row, col)

        # 填充空位
        remaining = len(self._cards) % self.columns
        if remaining:
            for j in range(remaining, self.columns):
                spacer = QWidget(self)
                spacer.setFixedSize(200, 180)
                self.layout.addWidget(
                    spacer,
                    len(self._cards) // self.columns, j
                )
