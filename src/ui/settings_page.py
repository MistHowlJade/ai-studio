"""设置页面 — 代理开关、模型配置、ComfyUI 设置、外观"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, StrongBodyLabel,
    BodyLabel, SettingCardGroup, SwitchSettingCard,
    ComboBoxSettingCard, LineEditSettingCard, PushSettingCard,
    ComboBox, PrimaryPushButton, InfoBar, InfoBarPosition,
    FluentIcon, setTheme, Theme,
)


class SettingsPage(ScrollArea):
    """设置页面"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

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

        layout.addWidget(appearanceGroup)

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

        InfoBar.success(
            title="已保存",
            content="设置已保存到 config.yaml",
            parent=self,
            position=InfoBarPosition.TOP,
        )
