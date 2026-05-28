"""控制台输出组件 — 等宽字体终端输出，支持 ANSI 颜色和自动裁剪"""
import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout


# ANSI 转义码 → QColor 映射
ANSI_COLORS = {
    # 标准色
    "30": QColor("#45475a"),  # 黑
    "31": QColor("#f38ba8"),  # 红
    "32": QColor("#a6e3a1"),  # 绿
    "33": QColor("#f9e2af"),  # 黄
    "34": QColor("#89b4fa"),  # 蓝
    "35": QColor("#cba6f7"),  # 紫
    "36": QColor("#94e2d5"),  # 青
    "37": QColor("#cdd6f4"),  # 白
    # 亮色
    "90": QColor("#585b70"),  # 亮黑（灰）
    "91": QColor("#f38ba8"),  # 亮红
    "92": QColor("#a6e3a1"),  # 亮绿
    "93": QColor("#f9e2af"),  # 亮黄
    "94": QColor("#89b4fa"),  # 亮蓝
    "95": QColor("#cba6f7"),  # 亮紫
    "96": QColor("#94e2d5"),  # 亮青
    "97": QColor("#ffffff"),  # 亮白
}

ANSI_BG_COLORS = {
    "40": QColor("#45475a"),
    "41": QColor("#f38ba8"),
    "42": QColor("#a6e3a1"),
    "43": QColor("#f9e2af"),
    "44": QColor("#89b4fa"),
    "45": QColor("#cba6f7"),
    "46": QColor("#94e2d5"),
    "47": QColor("#cdd6f4"),
    "100": QColor("#585b70"),
    "101": QColor("#f38ba8"),
    "102": QColor("#a6e3a1"),
    "103": QColor("#f9e2af"),
    "104": QColor("#89b4fa"),
    "105": QColor("#cba6f7"),
    "106": QColor("#94e2d5"),
    "107": QColor("#ffffff"),
}

# ANSI 正则：\x1b[<codes>m 或 \x1b[<codes>;<codes>m
ANSI_PATTERN = re.compile(r'\x1b\[([\d;]*)m')


class ConsoleOutput(QTextEdit):
    """等宽终端输出组件 — ANSI 颜色 + 自动裁剪 + 实时追加

    特性：
        - ANSI 转义码解析（SGR 颜色、粗体、斜体）
        - 自动裁剪（默认 10000 行上限）
        - 缓冲区追加（高效批量写入）
        - 可选自动滚动
    """

    def __init__(self, parent=None, max_lines=10000, auto_scroll=True):
        super().__init__(parent)
        self._max_lines = max_lines
        self._auto_scroll = auto_scroll
        self._ansi_state = {
            "fg": None, "bg": None, "bold": False, "italic": False
        }

        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
                font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", monospace;
                font-size: 13px;
                selection-background-color: #45475a;
            }
        """)

    def append_text(self, text):
        """追加文本，支持 ANSI"""
        self._trim_if_needed()
        self._insert_ansi_text(text)

        if self._auto_scroll:
            self._scroll_to_bottom()

    def append_html(self, html):
        """追加 HTML（无 ANSI 处理）"""
        self._trim_if_needed()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)

        if self._auto_scroll:
            self._scroll_to_bottom()

    def append_lines(self, lines: list[str]):
        """批量追加多行"""
        self._trim_if_needed()
        for line in lines:
            self._insert_ansi_text(line + "\n")

        if self._auto_scroll:
            self._scroll_to_bottom()

    def clear(self):
        """清空终端"""
        super().clear()
        self._ansi_state = {
            "fg": None, "bg": None, "bold": False, "italic": False
        }

    # ── ANSI 解析 ──

    def _insert_ansi_text(self, text):
        """解析 ANSI 转义码并插入格式化文本"""
        pos = 0
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#cdd6f4"))
        fmt.setFontWeight(QFont.Weight.Normal)
        fmt.setFontItalic(False)

        for match in ANSI_PATTERN.finditer(text):
            # 插入 ANSI 码之前的纯文本
            if match.start() > pos:
                plain = text[pos:match.start()]
                if plain:
                    cursor.insertText(plain, fmt)

            # 解析 ANSI 码
            codes_str = match.group(1)
            if codes_str:
                codes = [int(c) for c in codes_str.split(";") if c]
            else:
                codes = [0]  # \x1b[m = reset

            for code in codes:
                fmt = self._apply_sgr(code, fmt)

            pos = match.end()

        # 插入剩余文本
        if pos < len(text):
            cursor.insertText(text[pos:], fmt)

    def _apply_sgr(self, code, fmt):
        """应用单个 SGR 控制码"""
        if code == 0:  # 重置
            fmt.setForeground(QColor("#cdd6f4"))
            fmt.setBackground(QColor("#181825"))
            fmt.setFontWeight(QFont.Weight.Normal)
            fmt.setFontItalic(False)
            self._ansi_state = {
                "fg": None, "bg": None, "bold": False, "italic": False
            }

        elif code == 1:  # 粗体
            fmt.setFontWeight(QFont.Weight.Bold)
            self._ansi_state["bold"] = True

        elif code == 3:  # 斜体
            fmt.setFontItalic(True)
            self._ansi_state["italic"] = True

        elif code == 22:  # 取消粗体
            fmt.setFontWeight(QFont.Weight.Normal)
            self._ansi_state["bold"] = False

        elif code == 23:  # 取消斜体
            fmt.setFontItalic(False)
            self._ansi_state["italic"] = False

        elif 30 <= code <= 37 or 90 <= code <= 97:
            color = ANSI_COLORS.get(str(code))
            if color:
                fmt.setForeground(color)
                self._ansi_state["fg"] = code

        elif 40 <= code <= 47 or 100 <= code <= 107:
            color = ANSI_BG_COLORS.get(str(code))
            if color:
                fmt.setBackground(color)
                self._ansi_state["bg"] = code

        return fmt

    # ── 自动裁剪 ──

    def _trim_if_needed(self):
        """如果行数超过上限，删除前面的内容"""
        doc = self.document()
        if doc.blockCount() > self._max_lines:
            # 删除前 1000 行
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(1000):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Down,
                    QTextCursor.MoveMode.KeepAnchor
                )
            cursor.removeSelectedText()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        vbar = self.verticalScrollBar()
        vbar.setValue(vbar.maximum())
