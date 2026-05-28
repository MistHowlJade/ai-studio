"""设置页面 — 代理开关、模型配置、ComfyUI 设置、外观、历史浏览"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
)

from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, StrongBodyLabel,
    BodyLabel, SettingCardGroup, SwitchSettingCard,
    ComboBoxSettingCard, LineEditSettingCard, PushSettingCard,
    ComboBox, PrimaryPushButton, InfoBar, InfoBarPosition,
    FluentIcon, setTheme, Theme, CardWidget,
)


class SettingsPage(ScrollArea):
    """设置页面"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._session_store = None

        self.setObjectName("settingsPage")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.view = QWidget(self)
        self.setWidget(self.view)

        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(24)

        # 标题
        title = TitleLabel("⚙️ 设置", self.view)
        layout.addWidget(title)

        # ── 代理设置 ──
        agentGroup = SettingCardGroup("🤖 AI 代理", self.view)

        self.opencodeSwitch = SwitchSettingCard(
            FluentIcon.ROBOT, "OpenCode",
            "启用 OpenCode CLI 编程代理",
            config.get("agents.opencode.enabled", True),
            agentGroup,
        )
        agentGroup.addSettingCard(self.opencodeSwitch)

        self.hermesSwitch = SwitchSettingCard(
            FluentIcon.DEVELOPER_TOOLS, "Hermes",
            "启用 Hermes AGI 代理",
            config.get("agents.hermes.enabled", True),
            agentGroup,
        )
        agentGroup.addSettingCard(self.hermesSwitch)

        self.openclawSwitch = SwitchSettingCard(
            FluentIcon.COMMAND_PROMPT, "OpenClaw",
            "启用 OpenClaw 代理（如已迁移到 Hermes 可关闭）",
            config.get("agents.openclaw.enabled", True),
            agentGroup,
        )
        agentGroup.addSettingCard(self.openclawSwitch)

        layout.addWidget(agentGroup)

        # ── ComfyUI 设置 ──
        comfyGroup = SettingCardGroup("🎨 ComfyUI 创意工坊", self.view)

        # 远程模式开关
        self.comfyRemoteSwitch = SwitchSettingCard(
            FluentIcon.GLOBE, "远程模式",
            "连接到远程 ComfyUI 实例（关闭 = 使用本地 comfy CLI）",
            config.get("comfyui.remote_mode", False),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyRemoteSwitch)

        # 远程主机
        self.comfyHost = LineEditSettingCard(
            FluentIcon.LINK, "远程主机",
            "远程 ComfyUI 地址（仅远程模式）",
            config.get("comfyui.remote_host", ""),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyHost)

        # API Key
        self.comfyApiKey = LineEditSettingCard(
            FluentIcon.CERTIFICATE, "API Key",
            "远程 API 密钥（留空 = 无认证）",
            config.get("comfyui.api_key", ""),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyApiKey)

        self.comfyAutoStart = SwitchSettingCard(
            FluentIcon.POWER_BUTTON, "自动启动",
            "启动 AI Studio 时自动连接 ComfyUI",
            config.get("comfyui.auto_start", False),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyAutoStart)

        self.comfyPort = LineEditSettingCard(
            FluentIcon.LINK, "端口",
            "ComfyUI 服务端口（默认 8188）",
            str(config.get("comfyui.port", 8188)),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyPort)

        self.comfyWorkspace = LineEditSettingCard(
            FluentIcon.FOLDER, "工作目录",
            "本地 ComfyUI 安装路径",
            config.get("comfyui.workspace", "~/comfy/ComfyUI"),
            comfyGroup,
        )
        comfyGroup.addSettingCard(self.comfyWorkspace)

        layout.addWidget(comfyGroup)

        # ── 外观设置 ──
        appearanceGroup = SettingCardGroup("🎨 外观", self.view)

        self.themeSwitch = SwitchSettingCard(
            FluentIcon.BRUSH, "暗色主题",
            "切换暗色/亮色主题",
            config.get("general.theme", "dark") == "dark",
            appearanceGroup,
        )
        self.themeSwitch.checkedChanged.connect(self._on_theme_changed)
        appearanceGroup.addSettingCard(self.themeSwitch)

        # 字体大小
        fontLayout = QHBoxLayout()
        fontLayout.addWidget(BodyLabel("字体大小:", self.view))
        from PyQt6.QtWidgets import QSlider
        self._fontSlider = QSlider(Qt.Orientation.Horizontal, self.view)
        self._fontSlider.setRange(10, 20)
        self._fontSlider.setValue(config.get("general.font_size", 12))
        self._fontSlider.setFixedWidth(150)
        fontLayout.addWidget(self._fontSlider)
        self._fontLabel = BodyLabel(str(self._fontSlider.value()), self.view)
        self._fontSlider.valueChanged.connect(
            lambda v: self._fontLabel.setText(str(v))
        )
        fontLayout.addWidget(self._fontLabel)
        fontLayout.addStretch()
        appearanceGroup.layout().addLayout(fontLayout)

        self.themeAutoSwitch = SwitchSettingCard(
            FluentIcon.SYNC, "跟随系统主题",
            "自动跟随操作系统明暗模式切换",
            config.get("general.follow_system_theme", True),
            appearanceGroup,
        )
        appearanceGroup.addSettingCard(self.themeAutoSwitch)

        layout.addWidget(appearanceGroup)

        # ── 历史浏览 ──
        self._init_history_section(layout)

        # ── 保存按钮 ──
        btnLayout = QHBoxLayout()
        btnLayout.addStretch()

        saveBtn = PrimaryPushButton("保存设置", self.view)
        saveBtn.clicked.connect(self._save_settings)
        btnLayout.addWidget(saveBtn)

        layout.addLayout(btnLayout)
        layout.addStretch()

        # ── 底部信息 ──
        infoLabel = BodyLabel(
            "💡 设置自动保存到 ~/ai-platform/config.yaml", self.view
        )
        infoLabel.setStyleSheet("color: #585b70;")
        layout.addWidget(infoLabel)

    def _on_theme_changed(self, checked):
        if checked:
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)

    def _save_settings(self):
        """保存所有设置到配置文件"""
        self.config.set("agents.opencode.enabled", self.opencodeSwitch.isChecked())
        self.config.set("agents.hermes.enabled", self.hermesSwitch.isChecked())
        self.config.set("agents.openclaw.enabled", self.openclawSwitch.isChecked())
        self.config.set("comfyui.remote_mode", self.comfyRemoteSwitch.isChecked())
        self.config.set("comfyui.remote_host", self.comfyHost.lineEdit.text())
        self.config.set("comfyui.api_key", self.comfyApiKey.lineEdit.text())
        self.config.set("comfyui.auto_start", self.comfyAutoStart.isChecked())
        self.config.set("comfyui.port", int(self.comfyPort.lineEdit.text()))
        self.config.set("comfyui.workspace", self.comfyWorkspace.lineEdit.text())
        self.config.set(
            "general.theme",
            "dark" if self.themeSwitch.isChecked() else "light"
        )
        self.config.set("general.font_size", self._fontSlider.value())
        self.config.set(
            "general.follow_system_theme",
            self.themeAutoSwitch.isChecked(),
        )

        InfoBar.success(
            title="已保存",
            content="设置已保存到 config.yaml",
            parent=self,
            position=InfoBarPosition.TOP,
        )

    # ── 会话存储绑定 ──

    def set_session_store(self, store):
        """绑定会话存储"""
        self._session_store = store
        self._refresh_history()

    # ── 历史浏览 ──

    def _init_history_section(self, layout):
        """创建历史浏览 UI"""
        historyGroup = SettingCardGroup("📝 会话历史", self.view)

        # 搜索栏
        searchLayout = QHBoxLayout()
        self._historySearch = QLineEdit(self.view)
        self._historySearch.setPlaceholderText("搜索对话内容...")
        self._historySearch.returnPressed.connect(self._on_history_search)
        searchLayout.addWidget(self._historySearch)

        self._historyAgentFilter = ComboBox(self.view)
        self._historyAgentFilter.addItems(["全部", "hermes", "opencode", "openclaw"])
        self._historyAgentFilter.currentTextChanged.connect(self._on_history_search)
        self._historyAgentFilter.setFixedWidth(120)
        searchLayout.addWidget(self._historyAgentFilter)

        searchBtn = PrimaryPushButton("搜索", self.view)
        searchBtn.clicked.connect(self._on_history_search)
        searchLayout.addWidget(searchBtn)

        historyGroup.layout().addLayout(searchLayout)

        # 历史列表
        self._historyList = QListWidget(self.view)
        self._historyList.setMaximumHeight(300)
        self._historyList.itemClicked.connect(self._on_history_item_clicked)
        historyGroup.layout().addWidget(self._historyList)

        # 操作按钮
        actionLayout = QHBoxLayout()
        refreshBtn = QPushButton("刷新", self.view)
        refreshBtn.clicked.connect(self._refresh_history)
        actionLayout.addWidget(refreshBtn)

        deleteBtn = QPushButton("删除选中", self.view)
        deleteBtn.clicked.connect(self._on_history_delete)
        actionLayout.addWidget(deleteBtn)

        clearBtn = QPushButton("清空全部", self.view)
        clearBtn.setStyleSheet("color: #f38ba8;")
        clearBtn.clicked.connect(self._on_clear_history)
        actionLayout.addWidget(clearBtn)

        actionLayout.addStretch()
        historyGroup.layout().addLayout(actionLayout)

        layout.addWidget(historyGroup)

    def _refresh_history(self):
        """刷新历史列表"""
        if self._session_store is None:
            self._historyList.clear()
            return

        agent = self._historyAgentFilter.currentText()
        if agent == "全部":
            agent = None

        threads = self._session_store.list_threads(agent=agent, limit=50)
        self._historyList.clear()

        for t in threads:
            title = t.get("title", "(无标题)")
            agent_name = t.get("agent", "?")
            msgs = t.get("message_count", 0)
            time_str = t.get("updated_at", "")[:16]

            item = QListWidgetItem(
                f"[{agent_name}] {title}  — {msgs}条 · {time_str}"
            )
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self._historyList.addItem(item)

    def _on_history_search(self):
        """搜索历史"""
        if self._session_store is None:
            return

        query = self._historySearch.text().strip()
        agent = self._historyAgentFilter.currentText()
        if agent == "全部":
            agent = None

        if query:
            results = self._session_store.search(query, agent=agent, limit=30)
        else:
            self._refresh_history()
            return

        self._historyList.clear()

        seen = set()
        for r in results:
            tid = r["thread_id"]
            if tid in seen:
                continue
            seen.add(tid)

            content = r["content"][:60]
            item = QListWidgetItem(
                f"[{r.get('thread_agent', '?')}] 🔍 {content}..."
            )
            item.setData(Qt.ItemDataRole.UserRole, tid)
            self._historyList.addItem(item)

    def _on_history_item_clicked(self, item):
        """点击历史项 — 显示消息列表"""
        if self._session_store is None:
            return

        tid = item.data(Qt.ItemDataRole.UserRole)
        messages = self._session_store.get_messages(tid, limit=20)

        if not messages:
            return

        # 弹窗显示消息
        lines = [f"📝 共 {len(messages)} 条消息:\n"]
        for m in messages:
            role_icon = {"user": "👤", "assistant": "🤖", "system": "⚙️", "tool": "🔧"}
            icon = role_icon.get(m["role"], "❓")
            content = m["content"][:200] + ("..." if len(m["content"]) > 200 else "")
            lines.append(f"{icon} [{m['role']}] {content}")

        text = "\n".join(lines)
        InfoBar.info(
            title=f"对话 #{tid}",
            content=text[:500],
            parent=self,
            position=InfoBarPosition.TOP,
            duration=8000,
        )

    def _on_history_delete(self):
        """删除选中的线程"""
        if self._session_store is None:
            return

        item = self._historyList.currentItem()
        if not item:
            InfoBar.warning(
                title="未选择",
                content="请先选择一条对话",
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        tid = item.data(Qt.ItemDataRole.UserRole)
        self._session_store.delete_thread(tid)
        self._refresh_history()

        InfoBar.success(
            title="已删除",
            content=f"对话 #{tid} 已删除",
            parent=self,
            position=InfoBarPosition.TOP,
        )

    def _on_clear_history(self):
        """清空全部历史"""
        if self._session_store is None:
            return

        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有对话历史吗？此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        threads = self._session_store.list_threads(limit=999)
        for t in threads:
            self._session_store.delete_thread(t["id"])

        self._refresh_history()

        InfoBar.success(
            title="已清空",
            content=f"已删除 {len(threads)} 条对话",
            parent=self,
            position=InfoBarPosition.TOP,
        )
