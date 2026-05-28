# AI Studio — 通用 AI 桌面平台 实现计划

> **目标：** 构建一个 PyQt6 桌面应用，统一管理 OpenCode、OpenClaw、Hermes 三大 AI 编程代理，并集成 ComfyUI 视频/音频生成能力。

**架构：** Tab-based 多面板桌面应用，每个 AI 代理通过子进程 CLI 调用运行在独立面板中，ComfyUI 作为后台服务通过 REST API 驱动。共享配置层统一管理模型和 API key。

**技术栈：** Python 3.10+, PyQt6, PyYAML, aiohttp, QProcess (Qt 子进程管理), SQLite

**平台：** Linux (优先), macOS/Windows 后续适配

---

## 目录结构

```
~/ai-platform/
├── main.py                      # 入口
├── requirements.txt
├── config.yaml                  # 默认配置模板
├── README.md
├── src/
│   ├── __init__.py
│   ├── app.py                   # QApplication + 全局初始化
│   ├── config_manager.py        # 配置读写、校验
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py       # 主窗口：TabWidget + 状态栏
│   │   ├── agent_panel.py       # 通用代理面板基类
│   │   ├── opencode_panel.py    # OpenCode 专属面板
│   │   ├── hermes_panel.py      # Hermes 专属面板
│   │   ├── openclaw_panel.py    # OpenClaw 专属面板
│   │   ├── comfyui_panel.py     # 创意工坊面板（视频/音频）
│   │   ├── settings_dialog.py   # 全局设置对话框
│   │   └── output_widget.py     # 终端输出/日志组件
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py              # 抽象基类：子进程生命周期管理
│   │   ├── opencode.py          # opencode CLI 封装
│   │   ├── hermes.py            # hermes CLI 封装
│   │   └── openclaw.py          # openclaw CLI 封装
│   ├── media/
│   │   ├── __init__.py
│   │   ├── comfyui_manager.py   # ComfyUI 生命周期（启动/停止/状态）
│   │   ├── workflow_runner.py   # 工作流执行（参数注入 + 监控）
│   │   └── workflows/           # 预设工作流 JSON
│   └── storage/
│       ├── __init__.py
│       └── session_store.py     # SQLite 会话历史
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_agents.py
    └── test_comfyui.py
```

---

## 阶段一：项目骨架 + 配置系统

### Task 1.1: 初始化项目结构

**目标：** 创建项目目录、虚拟环境和依赖

```bash
mkdir -p ~/ai-platform/src/{ui,agents,media/workflows,storage}
mkdir -p ~/ai-platform/tests
cd ~/ai-platform
python3 -m venv .venv
source .venv/bin/activate
```

### Task 1.2: 创建 requirements.txt

**文件：** `~/ai-platform/requirements.txt`

```
PyQt6>=6.5
PyYAML>=6.0
aiohttp>=3.9
websocket-client>=1.6
Pillow>=10.0
```

安装：`pip install -r requirements.txt`

### Task 1.3: 实现配置管理器

**文件：** `~/ai-platform/src/config_manager.py`

配置结构 `config.yaml`:

```yaml
# AI 代理配置
agents:
  opencode:
    enabled: true
    model: "anthropic/claude-sonnet-4"
  openclaw:
    enabled: true
    model: "anthropic/claude-sonnet-4"
  hermes:
    enabled: true
    model: "anthropic/claude-sonnet-4"

# ComfyUI 配置
comfyui:
  host: "127.0.0.1"
  port: 8188
  workspace: "~/comfy/ComfyUI"
  auto_start: false

# 通用设置
general:
  theme: "dark"
  font_size: 12
  max_history: 1000
```

关键实现：
- `ConfigManager.load()` — 从 `~/ai-platform/config.yaml` 读取
- `ConfigManager.save()` — 写回
- `ConfigManager.get(key)` — 点号路径取值，如 `"agents.hermes.model"`
- `ConfigManager.set(key, value)` — 设置并自动保存

### Task 1.4: 创建应用入口

**文件：** `~/ai-platform/main.py`

```python
#!/usr/bin/env python3
import sys
from src.app import run

if __name__ == "__main__":
    sys.exit(run())
```

**文件：** `~/ai-platform/src/app.py`

```python
from PyQt6.QtWidgets import QApplication
from src.config_manager import ConfigManager
from src.ui.main_window import MainWindow

def run():
    app = QApplication([])
    app.setApplicationName("AI Studio")
    
    config = ConfigManager()
    config.load()
    
    window = MainWindow(config)
    window.show()
    
    return app.exec()
```

**验证：** `python main.py` — 应该打开一个空白窗口

---

## 阶段二：主窗口 + 面板框架

### Task 2.1: 实现主窗口

**文件：** `~/ai-platform/src/ui/main_window.py`

- `QMainWindow` + `QTabWidget`
- 5 个 Tab：OpenCode | OpenClaw | Hermes | 创意工坊 | 设置
- 底部状态栏显示 ComfyUI 状态、当前模型
- 菜单栏：文件（退出）、视图（主题切换）、帮助

```python
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QStatusBar, QMenuBar
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("AI Studio")
        self.resize(1200, 800)
        
        # Tab 面板
        self.tabs = QTabWidget()
        self.tabs.addTab(OpenCodePanel(config), "🤖 OpenCode")
        self.tabs.addTab(OpenClawPanel(config), "🦞 OpenClaw")
        self.tabs.addTab(HermesPanel(config), "⚡ Hermes")
        self.tabs.addTab(ComfyUIPanel(config), "🎨 创意工坊")
        self.tabs.addTab(SettingsDialog(config), "⚙️ 设置")
        self.setCentralWidget(self.tabs)
        
        # 状态栏
        self.status = QStatusBar()
        self.status.showMessage("就绪")
        self.setStatusBar(self.status)
```

### Task 2.2: 实现通用代理面板基类

**文件：** `~/ai-platform/src/ui/agent_panel.py`

每个代理面板的通用结构：
- 上方：模型选择下拉框 + 状态指示灯
- 中间：`QTextEdit` 输出日志区域
- 下方：输入框 + 发送按钮 + 停止按钮

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton,
    QComboBox, QLabel
)
from PyQt6.QtCore import pyqtSignal

class AgentPanel(QWidget):
    output_received = pyqtSignal(str)
    
    def __init__(self, config, agent_name):
        super().__init__()
        self.config = config
        self.agent_name = agent_name
        self.agent = None  # 由子类设置
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(["anthropic/claude-sonnet-4", "openai/gpt-4o", "deepseek-chat"])
        toolbar.addWidget(QLabel("模型:"))
        toolbar.addWidget(self.model_combo)
        toolbar.addStretch()
        self.status_led = QLabel("⚪")
        toolbar.addWidget(self.status_led)
        layout.addLayout(toolbar)
        
        # 输出区域
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入任务描述...")
        self.input_box.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input_box)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self.send_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        input_layout.addWidget(self.stop_btn)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
    
    def _on_send(self):
        prompt = self.input_box.text().strip()
        if not prompt:
            return
        self.input_box.clear()
        self.output_area.append(f"<b>你:</b> {prompt}")
        self.set_running(True)
        if self.agent:
            self.agent.run(prompt)
    
    def _on_stop(self):
        if self.agent:
            self.agent.stop()
        self.set_running(False)
    
    def set_running(self, running):
        self.status_led.setText("🟢" if running else "⚪")
        self.send_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
    
    def append_output(self, text):
        self.output_area.append(text)
```

---

## 阶段三：代理子进程引擎

### Task 3.1: 实现代理基类

**文件：** `~/ai-platform/src/agents/base.py`

用 `QProcess` 管理子进程，异步读取 stdout/stderr，信号驱动 UI 更新。

```python
from PyQt6.QtCore import QProcess, pyqtSignal, QObject

class BaseAgent(QObject):
    output_ready = pyqtSignal(str)
    finished = pyqtSignal(int)
    
    def __init__(self, workdir=None):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)
        self.workdir = workdir
    
    def run(self, prompt):
        """子类实现：构建命令并启动"""
        raise NotImplementedError
    
    def stop(self):
        self.process.kill()
    
    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data().decode()
        for line in data.split('\n'):
            if line.strip():
                self.output_ready.emit(line)
    
    def _on_stderr(self):
        data = self.process.readAllStandardError().data().decode()
        for line in data.split('\n'):
            if line.strip():
                self.output_ready.emit(f"[stderr] {line}")
    
    def _on_finished(self, exit_code):
        self.finished.emit(exit_code)
```

### Task 3.2: 实现 OpenCode 代理

**文件：** `~/ai-platform/src/agents/opencode.py`

```python
from src.agents.base import BaseAgent

class OpenCodeAgent(BaseAgent):
    def run(self, prompt, model=None):
        cmd = ["opencode", "run", prompt]
        if model:
            cmd.extend(["--model", model])
        self.process.start(cmd[0], cmd[1:])
```

### Task 3.3: 实现 Hermes 代理

**文件：** `~/ai-platform/src/agents/hermes.py`

```python
from src.agents.base import BaseAgent

class HermesAgent(BaseAgent):
    def run(self, prompt, model=None):
        cmd = ["hermes", "chat", "-q", prompt]
        if model:
            cmd.extend(["--model", model])
        self.process.start(cmd[0], cmd[1:])
```

### Task 3.4: 实现 OpenClaw 代理

**文件：** `~/ai-platform/src/agents/openclaw.py`

> **注意：** OpenClaw 的 CLI 接口待确认。如果已迁移到 Hermes，这个面板可作为 "备用模式"。先按类似的 CLI 接口实现。

```python
from src.agents.base import BaseAgent

class OpenClawAgent(BaseAgent):
    def run(self, prompt, model=None):
        # 先探测 openclaw 是否可用
        cmd = ["openclaw", "run", prompt]
        if model:
            cmd.extend(["--model", model])
        self.process.start(cmd[0], cmd[1:])
```

### Task 3.5: 代理面板对接 — OpenCode 面板

**文件：** `~/ai-platform/src/ui/opencode_panel.py`

```python
from src.ui.agent_panel import AgentPanel
from src.agents.opencode import OpenCodeAgent

class OpenCodePanel(AgentPanel):
    def __init__(self, config):
        super().__init__(config, "opencode")
        self.agent = OpenCodeAgent()
        self.agent.output_ready.connect(self.append_output)
        self.agent.finished.connect(lambda code: self.set_running(False))
```

---

## 阶段四：ComfyUI 创意工坊

### Task 4.1: ComfyUI 生命周期管理

**文件：** `~/ai-platform/src/media/comfyui_manager.py`

- 启动：`comfy launch --background`
- 停止：`comfy stop`
- 状态检测：`curl http://127.0.0.1:8188/system_stats`
- 信号：`server_started`, `server_stopped`, `server_error`

```python
from PyQt6.QtCore import QObject, pyqtSignal, QProcess
import requests

class ComfyUIManager(QObject):
    status_changed = pyqtSignal(str)  # "running", "stopped", "error"
    
    def __init__(self, workspace=None):
        super().__init__()
        self.workspace = workspace or "~/comfy/ComfyUI"
        self.host = "127.0.0.1"
        self.port = 8188
    
    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"
    
    def is_running(self):
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def start(self):
        self.process = QProcess()
        self.process.start("comfy", ["launch", "--background"])
    
    def stop(self):
        QProcess.startDetached("comfy", ["stop"])
```

### Task 4.2: 工作流执行器

**文件：** `~/ai-platform/src/media/workflow_runner.py`

- 加载工作流 JSON → 注入参数 → POST `/api/prompt` → WebSocket 监控进度 → 下载输出
- 支持：文生图、图生视频、音频生成

```python
import json, requests, uuid
from websocket import create_connection

class WorkflowRunner:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def run(self, workflow_path, params, on_progress=None, on_complete=None):
        with open(workflow_path) as f:
            workflow = json.load(f)
        
        # 注入参数
        workflow = self._inject_params(workflow, params)
        
        # 提交
        prompt_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": prompt_id}
        r = requests.post(f"{self.base_url}/prompt", json=payload)
        
        # WebSocket 监控进度
        ws = create_connection(f"ws://{self.base_url.replace('http://', '')}/ws?clientId={prompt_id}")
        ...
```

### Task 4.3: 创意工坊面板 UI

**文件：** `~/ai-platform/src/ui/comfyui_panel.py`

布局：
- 顶部：ComfyUI 启动/停止按钮 + 状态指示灯
- 左侧：工作流列表（预设 + 自定义导入）
- 右侧：参数编辑区 + 输出预览区
- 底部：执行按钮 + 进度条

预设工作流：
- `sd15_txt2img.json` — SD 1.5 文生图
- `sdxl_txt2img.json` — SDXL 文生图
- `flux_txt2img.json` — Flux 文生图
- `wan_t2v.json` — Wan 文生视频
- `hunyuan_t2v.json` — Hunyuan 文生视频
- `audio_generate.json` — 音频生成

### Task 4.4: 复制预设工作流

从 Hermes ComfyUI skill 的 `workflows/` 目录复制预设工作流：

```bash
cp ~/.hermes/skills/creative/comfyui/workflows/*.json ~/ai-platform/src/media/workflows/
```

---

## 阶段五：会话存储 + 历史

### Task 5.1: SQLite 会话存储

**文件：** `~/ai-platform/src/storage/session_store.py`

```python
import sqlite3
from datetime import datetime

class SessionStore:
    def __init__(self, db_path="~/ai-platform/sessions.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                prompt TEXT,
                response TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def save(self, agent, prompt, response, model):
        self.conn.execute(
            "INSERT INTO sessions (agent, prompt, response, model) VALUES (?,?,?,?)",
            (agent, prompt, response, model)
        )
        self.conn.commit()
    
    def get_history(self, agent=None, limit=50):
        query = "SELECT * FROM sessions"
        params = []
        if agent:
            query += " WHERE agent = ?"
            params.append(agent)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()
```

### Task 5.2: 在主窗口集成历史面板

在设置 Tab 中增加历史浏览功能，可按代理筛选，显示过往对话。

---

## 阶段六：设置 + 收尾

### Task 6.1: 全局设置对话框

**文件：** `~/ai-platform/src/ui/settings_dialog.py`

设置页包含：
- **代理设置** — 每个代理的 enabled/model 开关
- **ComfyUI 设置** — 端口、workspace、auto_start
- **外观设置** — 主题（dark/light）、字体大小
- **关于** — 版本信息、依赖检测

### Task 6.2: 依赖检测工具

**文件：** `~/ai-platform/src/config_manager.py` 增加 `check_deps()`

启动时自动检测：
- `opencode --version` ✅/❌
- `hermes --version` ✅/❌  
- `openclaw --version` ✅/❌
- `comfy --version` ✅/❌
- ComfyUI server 是否可达

在状态栏显示检测结果，未安装的代理在 Tab 上灰显。

### Task 6.3: 主题系统

使用 QSS (Qt Style Sheets) 实现暗色/亮色主题切换：

```python
def apply_dark_theme(app):
    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e2e; }
        QTextEdit, QLineEdit { 
            background-color: #2d2d3f; 
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 4px;
        }
        QPushButton {
            background-color: #45475a;
            color: #cdd6f4;
            border-radius: 4px;
            padding: 4px 12px;
        }
        QPushButton:hover { background-color: #585b70; }
        QTabWidget::pane { border: 1px solid #45475a; }
        QTabBar::tab {
            background-color: #2d2d3f;
            color: #a6adc8;
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: #1e1e2e;
            color: #cdd6f4;
            border-bottom: 2px solid #89b4fa;
        }
    """)
```

---

## 分阶段执行顺序总结

```
阶段一 (基础)     → Task 1.1-1.4    配置系统 + 应用入口
阶段二 (UI框架)   → Task 2.1-2.2    主窗口 + 面板框架
阶段三 (代理引擎) → Task 3.1-3.5    三个 AI 代理集成
阶段四 (创意工坊) → Task 4.1-4.4    ComfyUI 视频/音频
阶段五 (存储)     → Task 5.1-5.2    会话历史
阶段六 (收尾)     → Task 6.1-6.3    设置 + 主题 + 依赖检测
```

---

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| GUI 框架 | PyQt6 | 最成熟的 Python GUI，QProcess 天然适合子进程管理 |
| 子进程管理 | QProcess | Qt 原生异步 IPC，无需手动线程管理 |
| ComfyUI 通信 | REST + WebSocket | ComfyUI 原生协议，实时进度推送 |
| 配置格式 | YAML | 人类可读，PyYAML 成熟稳定 |
| 会话存储 | SQLite | 轻量零配置，适合个人使用 |
| 主题 | QSS 样式表 | Qt 原生机制，切换无需重启 |

## 风险 & 注意事项

1. **OpenClaw CLI 接口未确认** — 如果用户已迁移到 Hermes（`hermes claw migrate`），OpenClaw 面板可降级为 Hermes 的另一个工作区
2. **ComfyUI 需要 GPU** — 首次启动时做硬件检测，无 GPU 时提示使用 Comfy Cloud
3. **QProcess 跨平台差异** — Linux 优先开发，Windows 下路径和 shell 行为需单独适配
4. **大文件输出** — QTextEdit 累积大量文本会卡顿，需实现行数上限自动截断（保留最近 5000 行）
