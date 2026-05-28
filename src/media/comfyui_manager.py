"""ComfyUI 管理器 — 生命周期管理 + 队列监控 + GPU 检测"""
from PyQt6.QtCore import QObject, pyqtSignal, QProcess, QTimer
import requests
import shutil
import json


class ComfyUIManager(QObject):
    """ComfyUI 服务管理 — 本地 + 远程模式

    本地模式：通过 comfy CLI 启停
    远程模式：通过 HTTP API 连接远程实例

    信号：
        status_changed(str): "running", "stopped", "error", "starting", "connecting"
        queue_updated(dict): 队列状态
    """

    status_changed = pyqtSignal(str)
    queue_updated = pyqtSignal(dict)

    def __init__(
        self,
        workspace=None,
        host="127.0.0.1",
        port=8188,
        remote_mode=False,
        api_key=None,
    ):
        super().__init__()
        self.workspace = workspace or "~/comfy/ComfyUI"
        self.host = host
        self.port = port
        self.remote_mode = remote_mode
        self.api_key = api_key
        self.process = None
        self._check_timer = None
        self._queue_timer = None

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    # ── HTTP 请求辅助 ──

    def _request(self, method, path, **kwargs):
        """统一 HTTP 请求，自动附加 API Key"""
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}{path}"
        timeout = kwargs.pop("timeout", 10)

        try:
            return requests.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            )
        except requests.RequestException:
            return None

    # ── 状态检测 ──

    def is_running(self):
        """检测 ComfyUI 服务是否在运行"""
        resp = self._request("GET", "/system_stats", timeout=2)
        return resp is not None and resp.status_code == 200

    def get_system_stats(self):
        """获取系统统计（GPU 信息、显存等）"""
        resp = self._request("GET", "/system_stats", timeout=2)
        if resp and resp.status_code == 200:
            return resp.json()
        return None

    def get_queue_status(self):
        """获取当前队列状态"""
        resp = self._request("GET", "/queue", timeout=5)
        if resp and resp.status_code == 200:
            data = resp.json()
            self.queue_updated.emit(data)
            return data
        return {"queue_running": [], "queue_pending": []}

    # ── 生命周期 ──

    def start(self):
        """启动 ComfyUI（本地模式）或连接远程（远程模式）"""
        if self.remote_mode:
            self.connect_remote()
            return

        if self.is_running():
            self.status_changed.emit("running")
            self._start_queue_monitor()
            return

        self.process = QProcess(self)
        self.process.finished.connect(self._on_process_finished)
        self.process.start("comfy", ["launch", "--background"])
        self.status_changed.emit("starting")

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_startup)
        self._check_timer.start(2000)
        self._retry_count = 0

    def connect_remote(self):
        """连接到远程 ComfyUI 实例"""
        self.status_changed.emit("connecting")
        if self.is_running():
            self.status_changed.emit("running")
            self._start_queue_monitor()
        else:
            self.status_changed.emit("error")

    def disconnect_remote(self):
        """断开远程连接"""
        self._stop_queue_monitor()
        self.status_changed.emit("stopped")

    def stop(self):
        """停止 ComfyUI"""
        if self.remote_mode:
            self.disconnect_remote()
            return

        self._stop_queue_monitor()
        QProcess.startDetached("comfy", ["stop"])
        self.status_changed.emit("stopped")

    def _check_startup(self):
        """检测启动是否成功"""
        self._retry_count += 1
        if self.is_running():
            self._check_timer.stop()
            self._check_timer = None
            self.status_changed.emit("running")
            self._start_queue_monitor()
        elif self._retry_count > 30:
            self._check_timer.stop()
            self._check_timer = None
            self.status_changed.emit("error")

    def _on_process_finished(self, exit_code, exit_status):
        if self._check_timer:
            self._check_timer.stop()
            self._check_timer = None
        self._stop_queue_monitor()
        if not self.is_running():
            self.status_changed.emit("stopped")

    # ── 队列监控 ──

    def _start_queue_monitor(self):
        """启动队列轮询（每 2 秒）"""
        if not self._queue_timer:
            self._queue_timer = QTimer(self)
            self._queue_timer.timeout.connect(self.get_queue_status)
            self._queue_timer.start(2000)

    def _stop_queue_monitor(self):
        """停止队列轮询"""
        if self._queue_timer:
            self._queue_timer.stop()
            self._queue_timer = None

    # ── 硬件检测 ──

    @staticmethod
    def has_gpu():
        """检测是否有 NVIDIA GPU"""
        return shutil.which("nvidia-smi") is not None

    @staticmethod
    def get_gpu_memory():
        """获取 GPU 显存信息（MB）"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return int(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
        return None

    # ── 对象信息 ──

    def get_object_info(self):
        """获取 ComfyUI 节点/模型列表"""
        resp = self._request("GET", "/object_info", timeout=5)
        if resp and resp.status_code == 200:
            return resp.json()
        return {}
