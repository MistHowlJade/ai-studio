"""消息气泡组件 — 聊天气泡渲染，支持 Markdown 和代码高亮"""
import re

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor, QSyntaxHighlighter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QFrame, QScrollArea, QSizePolicy,
)


class MessageBubble(QFrame):
    """单个消息气泡

    支持角色配色（user/assistant/system/tool/error）
    自动左/右对齐，圆角气泡样式
    """

    def __init__(self, role, content, parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName(f"bubble_{role}")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 角色标签
        role_labels = {
            "user": "👤 你",
            "assistant": "🤖 AI",
            "system": "⚙️ 系统",
            "tool": "🔧 工具",
            "error": "❌ 错误",
        }
        role_name = role_labels.get(role, role)

        self.roleLabel = QLabel(role_name, self)
        role_colors = {
            "user": "#89b4fa",
            "assistant": "#a6e3a1",
            "system": "#f9e2af",
            "tool": "#94e2d5",
            "error": "#f38ba8",
        }
        color = role_colors.get(role, "#cdd6f4")
        self.roleLabel.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(self.roleLabel)

        # 内容区
        self.contentEdit = QTextEdit(self)
        self.contentEdit.setReadOnly(True)
        self.contentEdit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.contentEdit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.contentEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        # 渲染内容
        self._render_content(content)

        # 自动调整高度
        self.contentEdit.document().setDocumentMargin(4)
        self.contentEdit.setFixedHeight(
            int(self.contentEdit.document().size().height() + 8)
        )

        layout.addWidget(self.contentEdit)

        # 样式
        bg_colors = {
            "user": "#313244",
            "assistant": "#1e1e2e",
            "system": "#181825",
            "tool": "#1e1e2e",
            "error": "#2d1b1e",
        }
        bg = bg_colors.get(role, "#1e1e2e")
        align = "flex-end" if role == "user" else "flex-start"

        self.setStyleSheet(f"""
            QFrame#bubble_{role} {{
                background-color: {bg};
                border-radius: 12px;
                padding: 8px;
                margin: 4px 0px;
            }}
        """)

    def _render_content(self, content):
        """渲染消息内容，处理 Markdown 代码块"""
        html = self._markdown_to_html(content)
        self.contentEdit.setHtml(html)

    def _markdown_to_html(self, text):
        """简单的 Markdown → HTML 转换"""
        # 代码块 ```code```
        text = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<pre style="background:#181825;padding:8px;border-radius:6px;'
            r'color:#cdd6f4;font-family:monospace;font-size:12px;">'
            r'<code>\2</code></pre>',
            text, flags=re.DOTALL
        )

        # 行内代码 `code`
        text = re.sub(
            r'`([^`]+)`',
            r'<code style="background:#313244;padding:2px 6px;border-radius:3px;'
            r'font-family:monospace;font-size:12px;color:#f9e2af;">\1</code>',
            text
        )

        # 粗体 **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # 斜体 *text*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

        # 换行
        text = text.replace("\n", "<br>")

        return f'<span style="color:#cdd6f4;font-size:13px;">{text}</span>'


class ChatArea(QScrollArea):
    """聊天区域 — 消息气泡列表，自动滚动"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        # 内容容器
        self.container = QWidget(self)
        self.setWidget(self.container)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(4)
        self.layout.addStretch()

        self._bubbles = []
        self._max_bubbles = 200

    def add_message(self, role, content):
        """添加消息气泡"""
        bubble = MessageBubble(role, content, self.container)

        # 插入到 stretch 之前
        self.layout.insertWidget(self.layout.count() - 1, bubble)
        self._bubbles.append(bubble)

        # 限制数量，移除旧气泡
        while len(self._bubbles) > self._max_bubbles:
            old = self._bubbles.pop(0)
            self.layout.removeWidget(old)
            old.deleteLater()

        # 滚动到底部
        self._scroll_to_bottom()

    def add_system_message(self, content):
        """添加系统消息"""
        self.add_message("system", content)

    def add_error_message(self, content):
        """添加错误消息"""
        self.add_message("error", content)

    def clear(self):
        """清空所有消息"""
        for bubble in self._bubbles:
            self.layout.removeWidget(bubble)
            bubble.deleteLater()
        self._bubbles.clear()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.maximum())
