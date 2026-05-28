"""代理基类 — 基于 QProcess 的子进程管理，支持交互式控制"""
from PyQt6.QtCore import QProcess, pyqtSignal, QObject


class BaseAgent(QObject):
    """AI 代理基类，封装 QProcess 子进程完整生命周期

    信号：
        output_ready(str): 标准输出（逐行）
        error_ready(str): 标准错误（逐行）
        finished(int, str): 完成信号 (exit_code, status)
        status_changed(str): 状态变更 ("running", "finished", "error", "killed")
    """

    output_ready = pyqtSignal(str)
    error_ready = pyqtSignal(str)
    finished = pyqtSignal(int, str)
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.process = None
        self._is_running = False
        self._workdir = None
        self._model = None
        self._buffer = ""  # 行缓冲，处理跨块输出

    # ── 公共接口 ──

    @property
    def is_running(self):
        return self._is_running

    def run(
        self,
        prompt: str,
        model: str | None = None,
        workdir: str | None = None,
        **kwargs,
    ):
        """执行任务 — 子类实现 _build_command 后调用 _start_process"""
        raise NotImplementedError

    def stop(self):
        """停止正在运行的任务"""
        if self.process and self._is_running:
            self.process.kill()
            self._is_running = False
            self.status_changed.emit("killed")

    def write_stdin(self, text: str):
        """向正在运行的代理进程写入数据（用于交互式对话）"""
        if self.process and self._is_running:
            data = (text + "\n").encode("utf-8")
            self.process.write(data)

    def close_stdin(self):
        """关闭 stdin，通知进程输入结束"""
        if self.process and self._is_running:
            self.process.closeWriteChannel()

    # ── 子进程管理 ──

    def _start_process(self, command: list, workdir: str | None = None):
        """启动子进程并连接信号

        Args:
            command: [binary, arg1, arg2, ...]
            workdir: 工作目录（None 则继承当前目录）
        """
        self.process = QProcess(self)
        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )

        if workdir:
            self.process.setWorkingDirectory(workdir)

        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        self.process.start(command[0], command[1:])
        self._is_running = True
        self.status_changed.emit("running")

    def _read_stdout(self):
        """读取 stdout 并逐行发射"""
        data = bytes(self.process.readAllStandardOutput()).decode(
            errors="replace"
        )
        self._buffer += data
        self._flush_buffer("stdout")

    def _read_stderr(self):
        """读取 stderr 并逐行发射"""
        data = bytes(self.process.readAllStandardError()).decode(
            errors="replace"
        )
        for line in data.split("\n"):
            stripped = line.strip()
            if stripped:
                self.error_ready.emit(stripped)

    def _flush_buffer(self, source="stdout"):
        """将缓冲区按行分割并发射"""
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            stripped = line.strip()
            if stripped:
                if source == "stdout":
                    self.output_ready.emit(stripped)
                else:
                    self.error_ready.emit(stripped)

    def _on_finished(self, exit_code, exit_status):
        """进程完成处理"""
        # 刷新缓冲区剩余内容
        if self._buffer.strip():
            self.output_ready.emit(self._buffer.strip())
        self._buffer = ""

        self._is_running = False

        status_map = {
            QProcess.ExitStatus.NormalExit: "finished",
            QProcess.ExitStatus.CrashExit: "error",
        }
        status = status_map.get(exit_status, "finished")
        self.finished.emit(exit_code, status)
        self.status_changed.emit(status)

    def _on_error(self, error):
        """进程启动错误处理"""
        error_map = {
            QProcess.ProcessError.FailedToStart: "无法启动进程（检查 CLI 工具是否已安装）",
            QProcess.ProcessError.Crashed: "进程崩溃",
            QProcess.ProcessError.Timedout: "进程超时",
            QProcess.ProcessError.WriteError: "写入错误（stdin 已关闭）",
            QProcess.ProcessError.ReadError: "读取错误",
            QProcess.ProcessError.UnknownError: "未知错误",
        }
        msg = error_map.get(error, f"进程错误: {error}")
        self.error_ready.emit(msg)
        self._is_running = False
        self.status_changed.emit("error")
