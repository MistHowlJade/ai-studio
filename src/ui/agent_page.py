"""代理对话页面 — 通用 AI 代理对话界面，支持高级参数"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QLabel, QFileDialog,
)

from qfluentwidgets import (
    ScrollArea, TitleLabel, PushButton, PrimaryPushButton,
    ComboBox, InfoBar, InfoBarPosition, SwitchButton, ToolButton,
    FluentIcon, MessageBox, MessageBoxBase,
)


# 常用模型列表
COMMON_MODELS = [
    "Auto (默认)",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-opus-4",
    "openai/gpt-4o",
    "openai/gpt-4.1",
    "deepseek-chat",
    "deepseek-reasoner",
    "google/gemini-2.5-pro",
    "xai/grok-4",
]

# Hermes 常用 skill 列表
HERMES_SKILLS = [
    "(无)",
    "code-review",
    "codebase-inspection",
    "github-pr-workflow",
    "writing-plans",
    "systematic-debugging",
    "test-driven-development",
    "subagent-driven-development",
]


class AgentPage(ScrollArea):
    """代理对话页面 — 可复用于 OpenCode / Hermes / OpenClaw"""

    navigate_to = pyqtSignal(str)  # 导航到其他页面

    def __init__(self, config, agent_name, parent=None):
        super().__init__(parent)
        self.config = config
        self.agent_name = agent_name
        self.is_running = False
        self.agent_runner = None
        self._max_output_lines = 5000

        self.setObjectName(f"{agent_name}Page")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 主容器
        self.view = QWidget(self)
        self.setWidget(self.view)

        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(10)

        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()

        icons = {"opencode": "🤖", "hermes": "⚡", "openclaw": "🦞"}
        titles = {"opencode": "OpenCode", "hermes": "Hermes", "openclaw": "OpenClaw"}
        icon = icons.get(agent_name, "🤖")
        title = titles.get(agent_name, agent_name)

        titleLabel = TitleLabel(f"{icon}  {title}", self.view)
        toolbar.addWidget(titleLabel)

        toolbar.addStretch()

        # 模型选择
        modelLabel = QLabel("模型:", self.view)
        toolbar.addWidget(modelLabel)

        self.modelCombo = ComboBox(self.view)
        self.modelCombo.addItems(COMMON_MODELS)
        self.modelCombo.setFixedWidth(240)
        saved = config.get(f"agents.{agent_name}.model", "")
        if saved and saved in COMMON_MODELS:
            self.modelCombo.setText(saved)
        toolbar.addWidget(self.modelCombo)

        # 状态指示灯
        self.statusLed = QLabel("⚪", self.view)
        self.statusLed.setStyleSheet("font-size: 16px;")
        toolbar.addWidget(self.statusLed)

        layout.addLayout(toolbar)

        # ── 高级选项栏 ──
        advancedLayout = QHBoxLayout()
        advancedLayout.setSpacing(16)

        # Thinking 开关 (OpenCode + Hermes)
        if agent_name in ("opencode", "hermes"):
            thinkingLabel = QLabel("Thinking:", self.view)
            thinkingLabel.setStyleSheet("color: #a6adc8; font-size: 12px;")
            advancedLayout.addWidget(thinkingLabel)

            self.thinkingSwitch = SwitchButton(self.view)
            self.thinkingSwitch.setChecked(
                config.get(f"agents.{agent_name}.thinking", False)
            )
            advancedLayout.addWidget(self.thinkingSwitch)

            advancedLayout.addSpacing(8)

        # Skill 选择 (仅 Hermes)
        if agent_name == "hermes":
            skillLabel = QLabel("Skill:", self.view)
            skillLabel.setStyleSheet("color: #a6adc8; font-size: 12px;")
            advancedLayout.addWidget(skillLabel)

            self.skillCombo = ComboBox(self.view)
            self.skillCombo.addItems(HERMES_SKILLS)
            self.skillCombo.setFixedWidth(180)
            saved_skill = config.get(f"agents.{agent_name}.skill", "(无)")
            if saved_skill in HERMES_SKILLS:
                self.skillCombo.setText(saved_skill)
            advancedLayout.addWidget(self.skillCombo)

            advancedLayout.addSpacing(8)

        # 工作目录选择
        workdirLabel = QLabel("工作目录:", self.view)
        workdirLabel.setStyleSheet("color: #a6adc8; font-size: 12px;")
        advancedLayout.addWidget(workdirLabel)

        self.workdirInput = QLineEdit(self.view)
        self.workdirInput.setPlaceholderText("留空 = 当前目录")
        self.workdirInput.setFixedWidth(200)
        self.workdirInput.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #89b4fa; }
        """)
        advancedLayout.addWidget(self.workdirInput)

        browseBtn = ToolButton(FluentIcon.FOLDER, self.view)
        browseBtn.clicked.connect(self._browse_workdir)
        advancedLayout.addWidget(browseBtn)

        advancedLayout.addStretch()

        # 清空按钮
        clearBtn = PushButton("清空输出", self.view)
        clearBtn.clicked.connect(self._clear_output)
        advancedLayout.addWidget(clearBtn)

        layout.addLayout(advancedLayout)

        # ── 输出日志区 ──
        self.outputArea = QTextEdit(self.view)
        self.outputArea.setReadOnly(True)
        self.outputArea.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
                font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", monospace;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.outputArea, 1)

        # ── 输入区 ──
        inputLayout = QHBoxLayout()
        inputLayout.setSpacing(8)

        self.inputBox = QLineEdit(self.view)
        self.inputBox.setPlaceholderText("输入任务描述，按 Enter 发送...")
        self.inputBox.returnPressed.connect(self._on_send)
        self.inputBox.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        inputLayout.addWidget(self.inputBox, 1)

        self.sendBtn = PrimaryPushButton("发送", self.view)
        self.sendBtn.clicked.connect(self._on_send)
        inputLayout.addWidget(self.sendBtn)

        self.queueBtn = PushButton("加入队列", self.view)
        self.queueBtn.clicked.connect(self._submit_to_queue)
        inputLayout.addWidget(self.queueBtn)

        self.stopBtn = PushButton("停止", self.view)
        self.stopBtn.clicked.connect(self._on_stop)
        self.stopBtn.setEnabled(False)
        inputLayout.addWidget(self.stopBtn)

        layout.addLayout(inputLayout)

        # 提示信息
        hintLabel = QLabel(self._get_hint(), self.view)
        hintLabel.setStyleSheet("color: #585b70; font-size: 12px;")
        hintLabel.setWordWrap(True)
        layout.addWidget(hintLabel)

    def _get_hint(self):
        hints = {
            "opencode": '💡 使用 opencode CLI 执行编码任务。'
                        '请确保已安装: npm i -g opencode-ai',
            "hermes": '💡 使用 hermes CLI 执行任务。当前正在运行的就是 Hermes!\n'
                      '支持 --thinking 思考模式、-s skill 技能加载。',
            "openclaw": '💡 使用 openclaw CLI。'
                        '如已迁移到 Hermes (hermes claw migrate)，可直接用 Hermes 面板。',
        }
        return hints.get(self.agent_name, "")

    def _on_send(self):
        prompt = self.inputBox.text().strip()
        if not prompt or self.is_running:
            return

        self.inputBox.clear()
        self._append_message("你", prompt)
        self._set_running(True)

        # 创建代理
        agent_class_map = {
            "opencode": ("src.agents.opencode", "OpenCodeAgent"),
            "hermes": ("src.agents.hermes", "HermesAgent"),
            "openclaw": ("src.agents.openclaw", "OpenClawAgent"),
        }

        info = agent_class_map.get(self.agent_name)
        if not info:
            self._append_message("系统", f"❌ 未知代理: {self.agent_name}")
            self._set_running(False)
            return

        module_name, class_name = info
        module = __import__(module_name, fromlist=[class_name])
        AgentClass = getattr(module, class_name)
        self.agent_runner = AgentClass()

        # 连接信号
        self.agent_runner.output_ready.connect(self._on_output)
        self.agent_runner.error_ready.connect(self._on_stderr)
        self.agent_runner.finished.connect(self._on_finished)
        self.agent_runner.status_changed.connect(self._on_status_changed)

        # 收集参数
        model = self.modelCombo.currentText()
        if model == "Auto (默认)":
            model = None

        workdir = self.workdirInput.text().strip() or None

        kwargs = {"model": model, "workdir": workdir}

        if self.agent_name in ("opencode", "hermes"):
            kwargs["thinking"] = self.thinkingSwitch.isChecked()

        if self.agent_name == "hermes":
            skill = self.skillCombo.currentText()
            if skill != "(无)":
                kwargs["skill"] = skill

        self.agent_runner.run(prompt, **kwargs)

    def _on_stop(self):
        if self.agent_runner:
            self.agent_runner.stop()
        self._set_running(False)
        self._append_message("系统", "⏹ 已停止")

    def _on_output(self, text):
        self._trim_output()
        self.outputArea.append(
            f'<span style="color: #a6adc8;">{text}</span>'
        )

    def _on_stderr(self, text):
        self._trim_output()
        self.outputArea.append(
            f'<span style="color: #f38ba8;">[stderr] {text}</span>'
        )

    def _on_finished(self, exit_code, status):
        self._set_running(False)
        if exit_code == 0:
            self._append_message(
                self.agent_name.title(), "✅ 任务完成"
            )
        else:
            self._append_message(
                self.agent_name.title(),
                f"⚠️ 退出码: {exit_code} ({status})"
            )

    def _on_status_changed(self, status):
        status_map = {
            "running": ("🟢", True),
            "finished": ("⚪", False),
            "error": ("🔴", False),
            "killed": ("⏹", False),
        }
        led, running = status_map.get(status, ("⚪", False))
        self.statusLed.setText(led)

    def _set_running(self, running):
        self.is_running = running
        self.statusLed.setText("🟢" if running else "⚪")
        self.sendBtn.setEnabled(not running)
        self.stopBtn.setEnabled(running)
        self.modelCombo.setEnabled(not running)
        if hasattr(self, "thinkingSwitch"):
            self.thinkingSwitch.setEnabled(not running)
        if hasattr(self, "skillCombo"):
            self.skillCombo.setEnabled(not running)
        self.workdirInput.setEnabled(not running)

    def _append_message(self, sender, text):
        self._trim_output()
        colors = {
            "你": "#89b4fa",
            "系统": "#f9e2af",
            "Opencode": "#89b4fa",
            "Hermes": "#cba6f7",
            "Openclaw": "#f38ba8",
        }
        color = colors.get(sender, "#cdd6f4")
        self.outputArea.append(
            f'<p><b style="color: {color};">[{sender}]</b> '
            f'<span style="color: #cdd6f4;">{text}</span></p>'
        )

    def _trim_output(self):
        """防止 QTextEdit 行数过多导致 UI 卡顿"""
        doc = self.outputArea.document()
        if doc.blockCount() > self._max_output_lines:
            # 删除前 1000 行
            cursor = self.outputArea.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            for _ in range(1000):
                cursor.movePosition(
                    cursor.MoveOperation.Down,
                    cursor.MoveMode.KeepAnchor
                )
            cursor.removeSelectedText()

    def _clear_output(self):
        """清空输出区域"""
        self.outputArea.clear()

    def _browse_workdir(self):
        """浏览选择工作目录"""
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self.view, "选择工作目录", self.workdirInput.text() or "~"
        )
        if directory:
            self.workdirInput.setText(directory)

    def set_job_manager(self, manager):
        """绑定任务管理器 — 支持提交到队列"""
        self._job_manager = manager

    def set_session_store(self, store):
        """绑定会话存储"""
        self._session_store = store

    def _submit_to_queue(self):
        """提交当前输入到任务队列（而非直接执行）"""
        prompt = self.inputBox.text().strip()
        if not prompt:
            return

        if not hasattr(self, "_job_manager"):
            self._on_send()  # 降级为直接执行
            return

        self.inputBox.clear()
        self._append_message("你", prompt)

        model = self.modelCombo.currentText()
        if model == "Auto (默认)":
            model = None
        workdir = self.workdirInput.text().strip() or None

        kwargs = {}
        if self.agent_name in ("opencode", "hermes"):
            kwargs["thinking"] = self.thinkingSwitch.isChecked()
        if self.agent_name == "hermes":
            skill = self.skillCombo.currentText()
            if skill != "(无)":
                kwargs["skill"] = skill

        job_id = self._job_manager.submit(
            agent_name=self.agent_name,
            prompt=prompt,
            model=model,
            workdir=workdir,
            **kwargs,
        )
        self._append_message(
            "系统",
            f"📋 已提交到队列 (ID: {job_id})。查看首页任务面板。"
        )

    def check_availability(self):
        """检查代理 CLI 是否可用"""
        import shutil
        binary_map = {
            "opencode": "opencode",
            "hermes": "hermes",
            "openclaw": "openclaw",
        }
        binary = binary_map.get(self.agent_name)
        if binary:
            return shutil.which(binary) is not None
        return False
