# AI Studio — UI 设计研究报告

> 研究了 Cursor、LM Studio、Jan AI、Stable Diffusion WebUI、ChatGPT Desktop 等现代 AI 桌面应用的 UI 模式，以及 PyQt6 的现代化方案。

---

## 一、现代 AI 桌面应用的通用 UI 模式

### 布局范式：侧边栏导航 + 内容区

几乎所有现代桌面 AI 应用都采用**左侧导航 + 右侧内容**：

```
┌──────────────────────────────────────────────────┐
│ ┌─────────┐ ┌──────────────────────────────────┐ │
│ │  🏠 首页 │ │                                    │ │
│ │  🤖 代理 │ │        内容区                       │ │
│ │  🎨 创作 │ │    (对话/日志/预览/设置)            │ │
│ │         │ │                                    │ │
│ │         │ │                                    │ │
│ │         │ │                                    │ │
│ │  ⚙️ 设置 │ │                                    │ │
│ └─────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**参考来源：**
- Cursor、VS Code → 左侧文件树 + 右侧编辑区
- LM Studio → 左侧聊天列表 + 右侧对话区
- Jan AI → 侧边栏 + 对话面板
- Stable Diffusion WebUI → 顶部 Tab + 下方内容

### 为什么不用 Tab 导航？

Tab 导航（原方案）的问题：
- 代理多了 Tab 挤不下，需要滚动
- Tab 标签文字短，表达力不够
- 没有图标，辨识度低
- 现代桌面应用几乎不用 Top Tab 做主导航

**结论：改用侧边栏导航。**

---

## 二、PyQt6 现代化方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **纯手写 QSS** | 完全自由 | 工作量大，细节多 | ⭐⭐ |
| **QDarkStyleSheet** | 开箱即用，成熟 | 样式固定，不够现代 | ⭐⭐⭐ |
| **Qt Material** | Material Design 风格 | 和 AI 工具调性不太搭 | ⭐⭐ |
| **QFluentWidgets** ⭐ | Win11 Fluent 风格，组件丰富，7.9k⭐ | GPLv3 协议（个人使用无影响） | ⭐⭐⭐⭐⭐ |

### 强烈推荐：QFluentWidgets

- 内置 `FluentWindow`：侧边栏导航 + 内容区切换，即开即用
- 亚克力/Mica 半透明侧边栏特效
- 暗色/亮色主题自动切换
- 丰富的现代组件：卡片、按钮、输入框、对话框、进度环、信息条
- 支持启动闪屏（Splash Screen）

---

## 三、AI Studio 最终 UI 方案

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────┐
│ ┌──────────┐ ┌─────────────────────────────────────────┐ │
│ │          │ │  🔍 Toolbar: 标题 + 模型选择 + 状态指示   │ │
│ │  🏠 首页  │ │───────────────────────────────────────── │ │
│ │          │ │                                         │ │
│ │  🤖      │ │  ┌─────────────────────────────────────┐ │ │
│ │ OpenCode  │ │  │                                     │ │ │
│ │          │ │  │        对话 / 输出日志区域            │ │ │
│ │  ⚡      │ │  │        (monospace, 可滚动)           │ │ │
│ │ Hermes   │ │  │                                     │ │ │
│ │          │ │  └─────────────────────────────────────┘ │ │
│ │  🦞      │ │                                         │ │
│ │ OpenClaw │ │  ┌─────────────────────────────────────┐ │ │
│ │          │ │  │ [输入框___________________] [发送][停止]│ │
│ │ ──────── │ │  └─────────────────────────────────────┘ │ │
│ │  🎨 创意 │ │                                         │ │
│ │  工坊    │ ├───────────────────────────────────────── │ │
│ │          │ │  状态栏: ComfyUI ● | API ✓ | Model: xxx │ │
│ │ ──────── │ └─────────────────────────────────────────┘ │
│ │  ⚙️ 设置 │                                             │
│ └──────────┘                                             │
└─────────────────────────────────────────────────────────┘
```

### 3.2 五个子界面

| 导航项 | 图标 | 界面内容 |
|--------|------|---------|
| **首页** | 🏠 Home | Dashboard 概览：代理状态卡片、最近对话、快捷入口 |
| **OpenCode** | 🤖 Robot | 对话式终端：模型选择、输出日志、输入框、发送/停止 |
| **Hermes** | ⚡ Thunder | 同上，Hermes 专属面板 |
| **OpenClaw** | 🦞 Lobster | 同上，OpenClaw 专属面板 |
| **创意工坊** | 🎨 Palette | ComfyUI 控制面板：启动/停止、工作流选择、参数编辑、输出预览 |
| **设置** | ⚙️ Gear | 代理开关、模型配置、ComfyUI 设置、外观设置 |

### 3.3 首页 Dashboard 设计

```
┌─────────────────────────────────────────────────┐
│  🏠 AI Studio                                  │
│─────────────────────────────────────────────────│
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 🤖       │ │ ⚡       │ │ 🦞       │       │
│  │ OpenCode │ │ Hermes   │ │ OpenClaw │       │
│  │ ✅ 就绪  │ │ ✅ 就绪  │ │ ⚠️ 未安装│       │
│  │ [使用 →] │ │ [使用 →] │ │ [安装 →] │       │
│  └──────────┘ └──────────┘ └──────────┘       │
│                                                 │
│  ┌──────────────────────────┐                  │
│  │ 🎨 创意工坊              │                  │
│  │ ComfyUI ● 运行中         │                  │
│  │ [打开工坊 →]             │                  │
│  └──────────────────────────┘                  │
│                                                 │
│  ─── 最近对话 ──────────────────────────────── │
│  📝 OpenCode: "重构 auth 模块"    2 小时前     │
│  📝 Hermes: "写一份 GRPO 论文摘要"  昨天       │
│  📝 创意工坊: "生成赛博朋克猫"    昨天         │
└─────────────────────────────────────────────────┘
```

### 3.4 代理对话界面设计

```
┌─────────────────────────────────────────────────┐
│  🤖 OpenCode          模型: [Claude Sonnet ▼]  🟢│
│─────────────────────────────────────────────────│
│                                                 │
│  ─────────────────────────────────────────────  │
│  📤 你 (14:32)                                  │
│  帮我重构 auth 模块，加上 refresh token 逻辑    │
│  ─────────────────────────────────────────────  │
│  📥 OpenCode (14:32)                            │
│  正在分析 auth 模块...                          │
│  发现文件: src/auth/handler.py                  │
│  src/auth/token.py                              │
│                                                 │
│  重构计划:                                      │
│  1. 添加 RefreshToken 模型                      │
│  2. 创建 refresh_token 端点                     │
│  3. 更新中间件                                   │
│                                                 │
│  ...                                            │
│  ─────────────────────────────────────────────  │
│                                                 │
│  ┌──────────────────────────────────┐ [📎][发送]│
│  │ 输入任务描述...                   │ [⏹ 停止]│
│  └──────────────────────────────────┘          │
└─────────────────────────────────────────────────┘
```

### 3.5 创意工坊界面设计

```
┌─────────────────────────────────────────────────┐
│  🎨 创意工坊        ComfyUI ● 运行中  [启动][停止]│
│─────────────────────────────────────────────────│
│ ┌──────────────┐ ┌─────────────────────────────┐│
│ │ 📁 工作流     │ │  参数                        ││
│ │              │ │  Prompt: [______________]   ││
│ │ 🖼️ SDXL 文生图│ │  Negative: [_____________]   ││
│ │ 🎥 Wan 文生视频│ │  Steps: [30___]  Seed: [-1] ││
│ │ 🎵 音频生成   │ │  Size: [1024×1024 ▼]        ││
│ │ 🖼️ Flux 文生图│ │                              ││
│ │              │ │  [▶ 生成]                    ││
│ │ [+ 导入...]  │ │                              ││
│ └──────────────┘ ├─────────────────────────────┤│
│                  │  输出预览                     ││
│                  │  ┌─────────────────────┐    ││
│                  │  │   [生成的图片/视频]   │    ││
│                  │  │                     │    ││
│                  │  └─────────────────────┘    ││
│                  │  📁 输出目录: ./outputs/     ││
│                  └─────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

---

## 四、配色方案 (暗色主题)

参考 Cursor / VS Code / LM Studio 的暗色调，采用 Catppuccin Mocha 调色板：

| 用途 | 颜色 | 色值 |
|------|------|------|
| 窗口背景 | Base | `#1e1e2e` |
| 侧边栏背景 | Mantle | `#181825` |
| 卡片/输入框 | Surface0 | `#313244` |
| 边框/分隔线 | Surface1 | `#45475a` |
| 主要文字 | Text | `#cdd6f4` |
| 次要文字 | Subtext0 | `#a6adc8` |
| 强调色(蓝) | Blue | `#89b4fa` |
| 成功(绿) | Green | `#a6e3a1` |
| 警告(黄) | Yellow | `#f9e2af` |
| 错误(红) | Red | `#f38ba8` |
| 侧边栏激活 | Surface0 | `#313244` |

### QFluentWidgets 内置主题

QFluentWidgets 自带暗色/亮色主题切换，默认配色已经很好。可以在其基础上微调强调色。

```python
from qfluentwidgets import Theme, setTheme, setThemeColor

# 强制暗色
setTheme(Theme.DARK)

# 自定义强调色
setThemeColor('#89b4fa')  # Catppuccin Blue
```

---

## 五、组件选型 (QFluentWidgets)

| 需求 | 组件 | 说明 |
|------|------|------|
| 主窗口 | `FluentWindow` | 侧边栏 + 内容区，支持 Mica 特效 |
| 侧边栏导航 | `NavigationInterface` | 图标 + 文字，支持分组和分隔线 |
| 子界面容器 | `ScrollArea` | 带标题工具栏的可滚动内容区 |
| 代理状态卡片 | `CardWidget` | 首页 Dashboard 卡片 |
| 输入框 | `LineEdit` | 带 placeholder 的现代输入框 |
| 按钮 | `PrimaryPushButton` / `PushButton` | 主要/次要操作按钮 |
| 模型选择 | `ComboBox` | 下拉选择模型 |
| 输出日志 | `TextEdit` → 自建 `ConsoleWidget` | 等宽字体的终端风格输出区 |
| 工作流卡片 | `CardWidget` | 创意工坊中展示工作流 |
| 图片预览 | `ImageLabel` 或 自定义 `QLabel` | 显示生成的图片 |
| 进度环 | `ProgressRing` / `IndeterminateProgressRing` | 任务进行中 |
| 状态栏 | `StatusBar` 或自定义底部栏 | ComfyUI 状态、模型信息 |
| 设置 | `SettingCard` / `SwitchSettingCard` | 开关式设置项 |
| 对话框 | `MessageBox` / `Dialog` | 确认/提示弹窗 |
| 通知 | `InfoBar` | 成功/错误/警告通知条 |

---

## 六、技术实现要点

### 6.1 FluentWindow 基础结构

```python
from qfluentwidgets import FluentWindow, FluentIcon, NavigationItemPosition

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        # 子界面
        self.homePage = HomePage(self)
        self.opencodePage = AgentPage(self, "opencode")
        self.hermesPage = AgentPage(self, "hermes")
        self.openclawPage = AgentPage(self, "openclaw")
        self.comfyuiPage = ComfyUIPage(self)
        self.settingsPage = SettingsPage(self)
        
        self.initNavigation()
    
    def initNavigation(self):
        # 顶部导航组
        self.addSubInterface(self.homePage, FluentIcon.HOME, "首页")
        
        # 分隔线
        self.navigationInterface.addSeparator()
        
        # 代理组（可滚动区域）
        pos = NavigationItemPosition.SCROLL
        self.addSubInterface(self.opencodePage, FluentIcon.ROBOT, "OpenCode", pos)
        self.addSubInterface(self.hermesPage, FluentIcon.DEVELOPER_TOOLS, "Hermes", pos)
        self.addSubInterface(self.openclawPage, FluentIcon.COMMAND_PROMPT, "OpenClaw", pos)
        
        self.navigationInterface.addSeparator()
        self.addSubInterface(self.comfyuiPage, FluentIcon.PALETTE, "创意工坊", pos)
        
        # 底部固定
        self.addSubInterface(
            self.settingsPage, FluentIcon.SETTING, "设置",
            NavigationItemPosition.BOTTOM
        )
```

### 6.2 代理对话界面结构

```python
class AgentPage(QWidget):
    def __init__(self, parent, agent_name):
        super().__init__(parent)
        
        # 布局：垂直排列
        layout = QVBoxLayout(self)
        
        # 工具栏：标题 + 模型选择 + 状态灯
        toolbar = self._createToolbar()
        layout.addWidget(toolbar)
        
        # 对话区：ScrollArea + 消息气泡
        self.chatArea = self._createChatArea()
        layout.addWidget(self.chatArea)
        
        # 输入区：输入框 + 按钮
        inputBar = self._createInputBar()
        layout.addWidget(inputBar)
```

### 6.3 QProcess 异步通信

```python
class AgentRunner(QObject):
    outputReady = pyqtSignal(str)
    finished = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._readOutput)
        self.process.finished.connect(self._onFinished)
    
    def run(self, command: list):
        self.process.start(command[0], command[1:])
```

---

## 七、与原 Tab 方案的关键差异

| | 原方案 (QTabWidget) | 新方案 (FluentWindow) |
|---|---------------------|----------------------|
| **导航** | 顶部 Tab 标签 | 左侧图标 + 文字导航 |
| **扩展性** | 5个后拥挤 | 无上限，可滚动 |
| **视觉** | 传统桌面应用 | Win11 风格，Mica 特效 |
| **主题** | 手写 QSS | 内置自动暗/亮切换 |
| **首页** | 无 | Dashboard 概览卡片 |
| **组件库** | 基础 Qt 组件 | 丰富的 Fluent 组件 |

---

## 八、更新后的目录结构

```
~/ai-platform/
├── main.py
├── requirements.txt
├── config.yaml
├── src/
│   ├── app.py                    # QApplication + FluentWindow
│   ├── config_manager.py
│   ├── ui/
│   │   ├── main_window.py        # FluentWindow 子类
│   │   ├── home_page.py          # 首页 Dashboard
│   │   ├── agent_page.py         # 通用代理对话页面
│   │   ├── comfyui_page.py       # 创意工坊
│   │   ├── settings_page.py      # 设置页
│   │   └── widgets/
│   │       ├── chat_area.py      # 对话气泡组件
│   │       ├── console_output.py # 终端风格输出
│   │       └── workflow_card.py  # 工作流卡片
│   ├── agents/
│   │   ├── base.py
│   │   ├── opencode.py
│   │   ├── hermes.py
│   │   └── openclaw.py
│   ├── media/
│   │   ├── comfyui_manager.py
│   │   ├── workflow_runner.py
│   │   └── workflows/
│   └── storage/
│       └── session_store.py
```

新增依赖：
```
PyQt-Fluent-Widgets>=1.5    # Fluent Design 组件库
# 其余不变
```
