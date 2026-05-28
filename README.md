# AI Studio

一个基于 PyQt6 + QFluentWidgets 的桌面 AI 工作站，集成多种 AI 代理和 ComfyUI 创意工坊。

## 功能

- **多代理对话** — 同时运行 Hermes、OpenCode、OpenClaw，支持并行任务队列
- **创意工坊** — ComfyUI 本地/远程接入，预置 SDXL、Flux、Wan 等工作流
- **会话持久化** — SQLite 存储，全文搜索，多轮对话上下文
- **实时状态** — Dashboard 显示各代理可用性、活跃任务、ComfyUI 状态

## 快速启动

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动应用
bash launch.sh
```

## 依赖

- Python >= 3.10
- PyQt6 >= 6.5
- PyQt6-Fluent-Widgets >= 1.5
- PyYAML
- requests
- websocket-client
- Pillow

## 项目结构

```
ai-platform/
├── main.py                 # 入口
├── launch.sh               # 启动脚本
├── requirements.txt        # 依赖清单
├── PLAN.md                 # 开发计划
├── UI_DESIGN.md            # UI 设计文档
└── src/
    ├── app.py              # 应用核心
    ├── config_manager.py   # 配置管理
    ├── agents/             # AI 代理封装
    │   ├── base.py         # 代理基类
    │   ├── hermes.py       # Hermes Agent
    │   ├── opencode.py     # OpenCode CLI
    │   └── openclaw.py     # OpenClaw
    ├── jobs/               # 任务调度
    │   └── job_manager.py  # 并行任务管理器
    ├── media/              # 创意工坊
    │   ├── comfyui_manager.py  # ComfyUI 进程管理
    │   ├── workflow_runner.py  # 工作流执行
    │   └── workflows/      # 预置工作流 JSON
    ├── storage/            # 数据持久化
    │   └── session_store.py    # SQLite 会话存储
    └── ui/                 # 用户界面
        ├── main_window.py  # 主窗口
        ├── home_page.py    # 首页 Dashboard
        ├── agent_page.py   # 代理对话页
        ├── comfyui_page.py # 创意工坊页
        ├── settings_page.py # 设置页
        └── widgets/        # 自定义组件
            ├── chat_area.py
            ├── console_output.py
            ├── workflow_card.py
            └── job_panel.py
```

## 配置

首次运行会自动生成 `config.yaml`，支持配置：

- 各代理的 CLI 路径、默认参数
- ComfyUI 本地/远程模式、主机地址、API Key
- 并行任务并发数

## 许可证

MIT
