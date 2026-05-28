"""创意工坊 — ComfyUI 视频/音频生成控制面板（API 集成版）"""
import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QSplitter, QListWidget, QListWidgetItem,
)

from qfluentwidgets import (
    ScrollArea, TitleLabel, SubtitleLabel, StrongBodyLabel,
    BodyLabel, PrimaryPushButton, PushButton, CardWidget,
    ComboBox, InfoBar, InfoBarPosition, ProgressRing, FluentIcon,
)


# 预置工作流映射
WORKFLOW_REGISTRY = {
    "🖼️  SD 1.5 文生图": "sd15_txt2img.json",
    "🖼️  SDXL 文生图": "sdxl_txt2img.json",
    "🖼️  Flux Dev 文生图": "flux_txt2img.json",
    "🖼️  SDXL 图生图": "sdxl_img2img.json",
    "🖌️  SDXL 局部重绘": "sdxl_inpaint.json",
    "🔍  4x 超分辨率": "upscale_4x.json",
    "🎥  AnimateDiff 视频": "animatediff_video.json",
    "🎥  Wan 文生视频": "wan_txt2video.json",
}


class ComfyUIPage(ScrollArea):
    """创意工坊 — ComfyUI 管理 + 工作流执行"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.comfyui_manager = None
        self.workflow_runner = None
        self._current_workflow = None

        self.setObjectName("comfyuiPage")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.view = QWidget(self)
        self.setWidget(self.view)

        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()
        title = TitleLabel("🎨 创意工坊", self.view)
        toolbar.addWidget(title)
        toolbar.addStretch()

        self.statusLabel = BodyLabel("ComfyUI: 检测中...", self.view)
        toolbar.addWidget(self.statusLabel)

        self.startBtn = PrimaryPushButton("启动 ComfyUI", self.view)
        self.startBtn.clicked.connect(self._toggle_comfyui)
        toolbar.addWidget(self.startBtn)

        layout.addLayout(toolbar)

        subtitle = SubtitleLabel(
            "文生图 · 文生视频 · 音频生成 — 基于 ComfyUI 本地服务",
            self.view
        )
        layout.addWidget(subtitle)

        # ── 分栏：工作流列表 + 参数 + 预览 ──
        splitter = QSplitter(Qt.Orientation.Horizontal, self.view)

        # 左侧：工作流列表
        leftPanel = QWidget(splitter)
        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)

        leftTitle = StrongBodyLabel("📁 工作流", leftPanel)
        leftLayout.addWidget(leftTitle)

        self.workflowList = QListWidget(leftPanel)
        for name in WORKFLOW_REGISTRY:
            self.workflowList.addItem(name)
        self.workflowList.addItem("🎵  音频生成")
        self.workflowList.addItem("🎥  Hunyuan 文生视频")
        self.workflowList.currentItemChanged.connect(self._on_workflow_selected)
        self.workflowList.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
                color: #cdd6f4;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #313244;
            }
            QListWidget::item:hover {
                background-color: #45475a;
            }
        """)
        self.workflowList.setFixedWidth(200)
        leftLayout.addWidget(self.workflowList)

        # 导入按钮
        importBtn = PushButton("+ 导入工作流...", leftPanel)
        importBtn.clicked.connect(self._import_workflow)
        leftLayout.addWidget(importBtn)

        splitter.addWidget(leftPanel)

        # 中间：参数区
        midPanel = QWidget(splitter)
        midLayout = QVBoxLayout(midPanel)
        midLayout.setContentsMargins(12, 0, 12, 0)

        paramsTitle = StrongBodyLabel("⚙️ 参数", midPanel)
        midLayout.addWidget(paramsTitle)

        # Prompt
        midLayout.addWidget(BodyLabel("Prompt:", midPanel))
        self.promptInput = QLineEdit(midPanel)
        self.promptInput.setPlaceholderText("描述你想生成的内容...")
        self.promptInput.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus { border-color: #89b4fa; }
        """)
        midLayout.addWidget(self.promptInput)

        # Negative prompt
        midLayout.addWidget(BodyLabel("Negative Prompt:", midPanel))
        self.negPromptInput = QLineEdit(midPanel)
        self.negPromptInput.setPlaceholderText("不想看到的内容...")
        self.negPromptInput.setStyleSheet(self.promptInput.styleSheet())
        midLayout.addWidget(self.negPromptInput)

        # Steps & Seed
        stepsLayout = QHBoxLayout()
        stepsLayout.addWidget(BodyLabel("Steps:", midPanel))
        self.stepsCombo = ComboBox(midPanel)
        self.stepsCombo.addItems(["20", "30", "40", "50"])
        self.stepsCombo.setCurrentText("30")
        stepsLayout.addWidget(self.stepsCombo)

        stepsLayout.addSpacing(16)
        stepsLayout.addWidget(BodyLabel("Seed:", midPanel))
        self.seedInput = QLineEdit(midPanel)
        self.seedInput.setPlaceholderText("-1 = 随机")
        self.seedInput.setText("-1")
        self.seedInput.setFixedWidth(100)
        self.seedInput.setStyleSheet(self.promptInput.styleSheet())
        stepsLayout.addWidget(self.seedInput)
        stepsLayout.addStretch()
        midLayout.addLayout(stepsLayout)

        # CFG (for SDXL/Flux)
        cfgLayout = QHBoxLayout()
        cfgLayout.addWidget(BodyLabel("CFG:", midPanel))
        self.cfgCombo = ComboBox(midPanel)
        self.cfgCombo.addItems(["1.0", "3.0", "5.0", "7.0", "9.0", "12.0"])
        self.cfgCombo.setCurrentText("7.0")
        cfgLayout.addWidget(self.cfgCombo)
        cfgLayout.addStretch()
        midLayout.addLayout(cfgLayout)

        midLayout.addStretch()

        # 生成按钮 + 进度
        genLayout = QHBoxLayout()
        self.generateBtn = PrimaryPushButton("▶ 生成", midPanel)
        self.generateBtn.clicked.connect(self._on_generate)
        genLayout.addWidget(self.generateBtn)

        self.cancelBtn = PushButton("取消", midPanel)
        self.cancelBtn.clicked.connect(self._on_cancel)
        self.cancelBtn.setVisible(False)
        genLayout.addWidget(self.cancelBtn)

        genLayout.addStretch()
        midLayout.addLayout(genLayout)

        splitter.addWidget(midPanel)

        # 右侧：预览区
        rightPanel = QWidget(splitter)
        rightLayout = QVBoxLayout(rightPanel)
        rightLayout.setContentsMargins(12, 0, 0, 0)

        previewTitle = StrongBodyLabel("🖼️ 输出预览", rightPanel)
        rightLayout.addWidget(previewTitle)

        self.previewLabel = QLabel(rightPanel)
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                min-height: 200px;
                color: #585b70;
                font-size: 14px;
            }
        """)
        self.previewLabel.setText("生成的内容将显示在这里")
        rightLayout.addWidget(self.previewLabel, 1)

        # 进度条
        self.progressBar = QProgressBar(rightPanel)
        self.progressBar.setVisible(False)
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 4px;
                background-color: #1e1e2e;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
        """)
        rightLayout.addWidget(self.progressBar)

        splitter.addWidget(rightPanel)

        splitter.setSizes([220, 400, 400])
        layout.addWidget(splitter, 1)

        # 底部信息
        infoLabel = BodyLabel(
            "💡 ComfyUI 需要 NVIDIA GPU (≥6GB VRAM)。首次使用请先启动 ComfyUI 服务。",
            self.view
        )
        infoLabel.setStyleSheet("color: #585b70;")
        layout.addWidget(infoLabel)

    # ── ComfyUI 生命周期 ──

    def _toggle_comfyui(self):
        if self.comfyui_manager is None:
            from src.media.comfyui_manager import ComfyUIManager
            remote_mode = self.config.get("comfyui.remote_mode", False)
            host = self.config.get("comfyui.host", "127.0.0.1")
            port = self.config.get("comfyui.port", 8188)
            api_key = self.config.get("comfyui.api_key", None)
            self.comfyui_manager = ComfyUIManager(
                self.config.get("comfyui.workspace", "~/comfy/ComfyUI"),
                host=host,
                port=port,
                remote_mode=remote_mode,
                api_key=api_key,
            )
            self.comfyui_manager.status_changed.connect(
                self._on_comfyui_status
            )

        if self.comfyui_manager.is_running():
            self.comfyui_manager.stop()
        else:
            self.comfyui_manager.start()
            self.statusLabel.setText("ComfyUI: 🔄 连接中...")
            self.startBtn.setEnabled(False)

    def _on_comfyui_status(self, status):
        status_map = {
            "running": ("ComfyUI: 🟢 运行中", "停止 ComfyUI", True),
            "stopped": ("ComfyUI: ⚪ 已停止", "启动 ComfyUI", True),
            "starting": ("ComfyUI: 🔄 启动中...", "停止 ComfyUI", False),
            "error": ("ComfyUI: 🔴 启动失败", "启动 ComfyUI", True),
        }
        label, btn_text, enabled = status_map.get(
            status, (f"ComfyUI: {status}", "启动 ComfyUI", True)
        )
        self.statusLabel.setText(label)
        self.startBtn.setText(btn_text)
        self.startBtn.setEnabled(enabled)

    # ── 工作流生成 ──

    def _on_workflow_selected(self, current, previous):
        """工作流切换"""
        if current:
            self._current_workflow = current.text()

    def _on_generate(self):
        prompt = self.promptInput.text().strip()
        if not prompt:
            InfoBar.warning(
                title="提示", content="请输入 Prompt",
                parent=self, position=InfoBarPosition.TOP,
            )
            return

        if not self.comfyui_manager or not self.comfyui_manager.is_running():
            InfoBar.warning(
                title="ComfyUI 未运行",
                content="请先启动 ComfyUI 服务",
                parent=self, position=InfoBarPosition.TOP,
            )
            return

        # 加载工作流
        workflow_name = self._current_workflow
        if not workflow_name:
            workflow_name = self.workflowList.currentItem().text()

        wf_file = WORKFLOW_REGISTRY.get(workflow_name)
        if not wf_file:
            InfoBar.info(
                title="工作流",
                content=f"'{workflow_name}' 需要配置工作流文件",
                parent=self, position=InfoBarPosition.TOP,
            )
            return

        # 加载工作流 JSON
        wf_path = Path(__file__).parent.parent / "media" / "workflows" / wf_file
        if not wf_path.exists():
            InfoBar.error(
                title="错误",
                content=f"工作流文件不存在: {wf_file}",
                parent=self, position=InfoBarPosition.TOP,
            )
            return

        with open(wf_path, "r") as f:
            workflow = json.load(f)

        # 创建或重用 WorkflowRunner
        if self.workflow_runner is None:
            from src.media.workflow_runner import WorkflowRunner
            host = self.config.get("comfyui.host", "127.0.0.1")
            port = self.config.get("comfyui.port", 8188)
            self.workflow_runner = WorkflowRunner(host, port)
            self.workflow_runner.progress_updated.connect(
                self._on_progress
            )
            self.workflow_runner.node_progress.connect(
                self._on_node_progress
            )
            self.workflow_runner.preview_ready.connect(
                self._on_preview
            )
            self.workflow_runner.outputs_ready.connect(
                self._on_outputs
            )
            self.workflow_runner.finished.connect(
                self._on_generation_finished
            )
            self.workflow_runner.error_occurred.connect(
                self._on_generation_error
            )

        if self.workflow_runner.is_running:
            InfoBar.warning(
                title="繁忙",
                content="已有生成任务在运行，请等待完成",
                parent=self, position=InfoBarPosition.TOP,
            )
            return

        # 解析参数
        seed = int(self.seedInput.text())
        neg_prompt = self.negPromptInput.text().strip()

        self._set_generating(True)

        self.workflow_runner.execute(
            workflow,
            prompt_text=prompt,
            negative_prompt=neg_prompt,
            seed=seed,
        )

    def _on_cancel(self):
        if self.workflow_runner:
            self.workflow_runner.cancel()

    def _set_generating(self, active):
        self.generateBtn.setVisible(not active)
        self.cancelBtn.setVisible(active)
        self.progressBar.setVisible(active)
        if active:
            self.progressBar.setRange(0, 0)  # 不确定进度

    def _on_progress(self, value, maximum):
        self.progressBar.setRange(0, maximum)
        self.progressBar.setValue(value)

    def _on_node_progress(self, node_id, completed, total):
        self.progressBar.setRange(0, total)
        self.progressBar.setValue(completed)

    def _on_preview(self, image_path):
        """显示预览图"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                400, 400, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.previewLabel.setPixmap(scaled)

    def _on_outputs(self, outputs):
        """显示所有输出"""
        paths = []
        for node_id, files in outputs.items():
            paths.extend(files)

        InfoBar.success(
            title="生成完成",
            content=f"已生成 {len(paths)} 个文件",
            parent=self, position=InfoBarPosition.TOP,
        )

    def _on_generation_finished(self, success):
        self._set_generating(False)
        if success:
            self.progressBar.setValue(self.progressBar.maximum())

    def _on_generation_error(self, msg):
        self._set_generating(False)
        InfoBar.error(
            title="生成失败", content=msg,
            parent=self, position=InfoBarPosition.TOP,
        )

    def _import_workflow(self):
        """导入自定义工作流 JSON"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "导入工作流 JSON", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            name = os.path.basename(file_path)
            self.workflowList.insertItem(0, f"📥 {name}")
            WORKFLOW_REGISTRY[f"📥 {name}"] = file_path
            InfoBar.success(
                title="已导入", content=f"工作流: {name}",
                parent=self, position=InfoBarPosition.TOP,
            )

    def check_availability(self):
        """检查 ComfyUI CLI 是否可用"""
        return shutil.which("comfy") is not None


# 保持 shutil which 可用
import shutil
