"""ComfyUI 工作流执行器 — REST API + WebSocket 进度 + 图片下载"""
import json
import time
import uuid
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMutex

import requests

# WebSocket 是可选的；没有安装时降级为轮询模式
try:
    from websocket import create_connection, WebSocket
    _HAS_WEBSOCKET = True
except ImportError:
    _HAS_WEBSOCKET = False


class WorkflowRunner(QObject):
    """ComfyUI 工作流执行器 — 提交工作流 → 监控进度 → 下载结果

    信号：
        progress_updated(int, int): (step, total_steps)
        execution_started(str): prompt_id
        node_progress(str, int, int): (node_name, progress, max)
        preview_ready(str): 预览图片本地路径
        outputs_ready(dict): {node_id: [file_paths]}
        finished(bool): 成功/失败
        error_occurred(str): 错误消息

    用法：
        runner = WorkflowRunner("127.0.0.1", 8188)
        runner.progress_updated.connect(on_progress)
        runner.finished.connect(on_done)
        runner.execute(workflow_json, prompt_text="a cat")
    """

    progress_updated = pyqtSignal(int, int)
    execution_started = pyqtSignal(str)
    node_progress = pyqtSignal(str, int, int)
    preview_ready = pyqtSignal(str)
    outputs_ready = pyqtSignal(dict)
    finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, host="127.0.0.1", port=8188, output_dir=None, api_key=None):
        super().__init__()
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
        self.output_dir = Path(output_dir) if output_dir else \
            Path.home() / "ai-platform" / "outputs" / "comfyui"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._thread = None
        self._worker = None
        self._running = False

    @property
    def is_running(self):
        return self._running

    def execute(
        self,
        workflow: dict,
        prompt_text: str = "",
        negative_prompt: str = "",
        seed: int = -1,
        extra_params: dict | None = None,
    ):
        """提交工作流并开始执行

        Args:
            workflow: ComfyUI 工作流 JSON（API 格式）
            prompt_text: 正向提示词（自动注入 workflow 中的 CLIPTextEncode 节点）
            negative_prompt: 反向提示词
            seed: 随机种子（-1 随机，自动注入 KSampler 节点）
            extra_params: 额外节点参数覆盖
        """
        if self._running:
            self.error_occurred.emit("已有任务正在运行")
            return

        self._running = True

        # 注入提示词和种子到工作流
        workflow = self._inject_params(
            workflow, prompt_text, negative_prompt, seed, extra_params
        )

        # 在工作线程中执行
        self._worker = _ExecutionWorker(
            self.base_url, workflow, self.output_dir,
            _HAS_WEBSOCKET, self.api_key
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        # 连接信号
        self._worker.progress.connect(self.progress_updated)
        self._worker.started_signal.connect(self.execution_started)
        self._worker.node_progress.connect(self.node_progress)
        self._worker.preview.connect(self.preview_ready)
        self._worker.outputs.connect(self.outputs_ready)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)

        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def cancel(self):
        """取消当前执行（中断 WebSocket 连接）"""
        if self._worker:
            self._worker.cancel()
        self._running = False

    def _on_worker_finished(self, success: bool):
        self._running = False
        self._cleanup_thread()
        self.finished.emit(success)

    def _on_worker_error(self, msg: str):
        self._running = False
        self._cleanup_thread()
        self.error_occurred.emit(msg)

    def _cleanup_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        self._thread = None
        self._worker = None

    # ── 工作流参数注入 ──

    def _inject_params(
        self, workflow, prompt, neg_prompt, seed, extra_params
    ):
        """自动注入提示词和种子到工作流节点"""
        wf = json.loads(json.dumps(workflow))  # 深拷贝

        for node_id, node in wf.items():
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})

            # CLIPTextEncode → 注入 prompt
            if class_type == "CLIPTextEncode" and prompt:
                # 第一个 CLIPTextEncode 通常为正提示词
                if inputs.get("text", "") in ("", "CLIP_TEXT_POSITIVE"):
                    inputs["text"] = prompt
                elif neg_prompt and inputs.get("text", "") in ("", "CLIP_TEXT_NEGATIVE"):
                    inputs["text"] = neg_prompt

            # KSampler → 注入 seed
            if class_type in ("KSampler", "KSamplerAdvanced") and seed != -1:
                inputs["seed"] = seed

            # 额外参数覆盖
            if extra_params and node_id in extra_params:
                inputs.update(extra_params[node_id])

        return wf


class _ExecutionWorker(QObject):
    """工作线程：提交工作流 → WebSocket 监听 → 下载输出"""

    progress = pyqtSignal(int, int)
    started_signal = pyqtSignal(str)
    node_progress = pyqtSignal(str, int, int)
    preview = pyqtSignal(str)
    outputs = pyqtSignal(dict)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, base_url, workflow, output_dir, use_ws, api_key=None):
        super().__init__()
        self.base_url = base_url
        self.workflow = workflow
        self.output_dir = output_dir
        self.use_ws = use_ws
        self.api_key = api_key
        self._cancelled = False
        self._mutex = QMutex()

    def cancel(self):
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()

    def _is_cancelled(self):
        self._mutex.lock()
        val = self._cancelled
        self._mutex.unlock()
        return val

    def run(self):
        """主执行流程"""
        try:
            # 1. 提交工作流
            prompt_id = self._queue_prompt()
            if not prompt_id:
                self.error.emit("提交工作流失败")
                self.finished.emit(False)
                return

            self.started_signal.emit(prompt_id)

            # 2. 监控进度
            if self.use_ws:
                outputs_by_node = self._monitor_ws(prompt_id)
            else:
                outputs_by_node = self._monitor_poll(prompt_id)

            if self._is_cancelled():
                self.error.emit("任务已取消")
                self.finished.emit(False)
                return

            # 3. 下载输出
            downloaded = self._download_outputs(outputs_by_node)
            self.outputs.emit(downloaded)
            self.finished.emit(True)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)

    # ── API 调用 ──

    def _queue_prompt(self):
        """POST /api/prompt — 提交工作流"""
        payload = {
            "prompt": self.workflow,
            "client_id": str(uuid.uuid4()),
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json=payload, timeout=10, headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("prompt_id")
        except requests.RequestException:
            pass
        return None

    def _get_history(self, prompt_id):
        """GET /api/history/{prompt_id} — 获取执行历史"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=10, headers=headers
            )
            if resp.status_code == 200:
                return resp.json().get(prompt_id, {})
        except requests.RequestException:
            pass
        return {}

    def _get_queue(self):
        """GET /api/queue — 获取队列状态"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.get(
                f"{self.base_url}/queue", timeout=5, headers=headers
            )
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return {}

    # ── WebSocket 进度监控 ──

    def _monitor_ws(self, prompt_id):
        """通过 WebSocket 监听执行进度"""
        ws_url = f"ws://{self.base_url.split('://')[1]}/ws?clientId={prompt_id}"

        try:
            ws = create_connection(ws_url, timeout=10)
        except Exception:
            # WebSocket 连接失败，降级为轮询
            return self._monitor_poll(prompt_id)

        outputs_by_node = {}
        total_nodes = len(self.workflow)
        completed_nodes = 0

        try:
            while not self._is_cancelled():
                try:
                    ws.settimeout(2.0)
                    msg = ws.recv()
                except Exception:
                    # 超时或连接关闭
                    break

                if not msg:
                    break

                data = json.loads(msg)
                msg_type = data.get("type", "")

                if msg_type == "executing":
                    node_id = data.get("data", {}).get("node")
                    if node_id:
                        completed_nodes += 1
                        self.node_progress.emit(
                            node_id, completed_nodes, total_nodes
                        )
                        self.progress.emit(completed_nodes, total_nodes)

                elif msg_type == "executed":
                    node_output = data.get("data", {}).get("output", {})
                    node_id = data.get("data", {}).get("node")
                    if node_output and "images" in node_output:
                        outputs_by_node[node_id] = node_output["images"]

                elif msg_type == "progress":
                    val = data.get("data", {}).get("value", 0)
                    max_val = data.get("data", {}).get("max", 1)
                    self.progress.emit(val, max_val)

        finally:
            ws.close()

        return outputs_by_node

    # ── 轮询进度（WebSocket 不可用时的降级方案）──

    def _monitor_poll(self, prompt_id):
        """轮询 /api/history 检查执行状态"""
        outputs_by_node = {}
        max_checks = 300  # 最多等 10 分钟（2s 间隔）

        for _ in range(max_checks):
            if self._is_cancelled():
                break

            history = self._get_history(prompt_id)
            if history:
                outputs = history.get("outputs", {})
                for node_id, output in outputs.items():
                    if "images" in output:
                        outputs_by_node[node_id] = output["images"]

                self.progress.emit(1, 1)  # 完成
                break

            time.sleep(2)

        return outputs_by_node

    # ── 图片下载 ──

    def _download_outputs(self, outputs_by_node):
        """下载所有输出图片到本地"""
        downloaded = {}

        for node_id, images in outputs_by_node.items():
            files = []
            for img_info in images:
                filename = img_info.get("filename", "")
                subfolder = img_info.get("subfolder", "")
                img_type = img_info.get("type", "output")

                if not filename:
                    continue

                # 构建 URL
                params = f"filename={filename}&type={img_type}"
                if subfolder:
                    params += f"&subfolder={subfolder}"

                try:
                    headers = {}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    resp = requests.get(
                        f"{self.base_url}/view?{params}",
                        timeout=30, headers=headers
                    )
                    if resp.status_code == 200:
                        # 保存到本地
                        local_path = self.output_dir / filename
                        local_path.write_bytes(resp.content)
                        files.append(str(local_path))

                        # 第一张图作为预览
                        if not downloaded:
                            self.preview.emit(str(local_path))
                except requests.RequestException:
                    pass

            if files:
                downloaded[node_id] = files

        return downloaded
