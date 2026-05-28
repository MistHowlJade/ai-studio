"""任务管理器 — 多代理并行调度、队列管理、状态追踪

每个任务拥有独立的 Agent 实例和 QProcess，真正的并行执行。
支持：提交 → 排队 → 并行运行 → 完成/失败追踪。
"""
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """单个任务描述"""
    job_id: str
    agent_name: str  # "opencode" | "hermes" | "openclaw"
    prompt: str
    model: str | None = None
    workdir: str | None = None
    skill: str | None = None
    thinking: bool = False
    status: JobStatus = JobStatus.PENDING
    exit_code: int | None = None
    error_message: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    output_lines: list[str] = field(default_factory=list)

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return 0

    @property
    def duration_str(self):
        d = self.duration
        if d < 60:
            return f"{d:.0f}s"
        elif d < 3600:
            return f"{d / 60:.1f}m"
        return f"{d / 3600:.1f}h"


class JobManager(QObject):
    """多代理并行任务管理器

    信号：
        job_submitted(str): 任务已提交
        job_started(str): 任务开始执行
        job_output(str, str): (job_id, output_line)
        job_error(str, str): (job_id, error_message)
        job_finished(str, JobStatus): 任务完成/失败/取消
        job_progress(str, dict): 任务进度更新（完整 job 数据）

    特性：
        - 无上限并行（每个任务独立 QProcess，真正的并行）
        - 可选最大并发数（max_concurrent）
        - 自动清理已完成任务
    """

    job_submitted = pyqtSignal(str)
    job_started = pyqtSignal(str)
    job_output = pyqtSignal(str, str)
    job_error = pyqtSignal(str, str)
    job_finished = pyqtSignal(str, str)  # job_id, status value
    job_progress = pyqtSignal(str, dict)

    def __init__(self, max_concurrent: int = 0):
        """
        Args:
            max_concurrent: 最大并行数（0 = 无限制）
        """
        super().__init__()
        self.max_concurrent = max_concurrent
        self._jobs: dict[str, Job] = {}
        self._runners: dict[str, object] = {}  # job_id → Agent instance
        self._pending_queue: list[str] = []

    # ── 任务提交 ──

    def submit(
        self,
        agent_name: str,
        prompt: str,
        model: str | None = None,
        workdir: str | None = None,
        skill: str | None = None,
        thinking: bool = False,
    ) -> str:
        """提交新任务，返回 job_id

        Args:
            agent_name: "opencode" | "hermes" | "openclaw"
            prompt: 任务描述
            model: 模型名称
            workdir: 工作目录
            skill: 技能名称（仅 Hermes）
            thinking: 思考模式（OpenCode/Hermes）
        """
        job_id = str(uuid.uuid4())[:8]

        job = Job(
            job_id=job_id,
            agent_name=agent_name,
            prompt=prompt,
            model=model,
            workdir=workdir,
            skill=skill,
            thinking=thinking,
        )
        self._jobs[job_id] = job
        self.job_submitted.emit(job_id)

        # 检查并发限制
        running = self._count_running()
        if self.max_concurrent > 0 and running >= self.max_concurrent:
            self._pending_queue.append(job_id)
        else:
            self._start_job(job_id)

        return job_id

    def cancel(self, job_id: str):
        """取消任务"""
        job = self._jobs.get(job_id)
        if not job:
            return

        if job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            if job_id in self._pending_queue:
                self._pending_queue.remove(job_id)
            self.job_finished.emit(job_id, JobStatus.CANCELLED.value)
            self._maybe_start_next()

        elif job.status == JobStatus.RUNNING:
            runner = self._runners.get(job_id)
            if runner:
                runner.stop()
            job.status = JobStatus.CANCELLED
            job.finished_at = time.time()
            self.job_finished.emit(job_id, JobStatus.CANCELLED.value)
            self._runners.pop(job_id, None)
            self._maybe_start_next()

    # ── 任务查询 ──

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def get_jobs(self, status: JobStatus | None = None) -> list[Job]:
        """获取所有任务，可按状态过滤"""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def get_active_jobs(self) -> list[Job]:
        """获取活跃任务（pending + running）"""
        return [
            j for j in self._jobs.values()
            if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
        ]

    def get_recent_jobs(self, limit: int = 20) -> list[Job]:
        """获取最近任务"""
        return sorted(
            self._jobs.values(),
            key=lambda j: j.created_at, reverse=True
        )[:limit]

    def get_running_count(self) -> int:
        return self._count_running()

    def get_queue_size(self) -> int:
        return len(self._pending_queue)

    # ── 统计 ──

    def get_stats(self) -> dict:
        """获取任务统计"""
        jobs = self._jobs.values()
        per_status = {}
        per_agent = {}
        for j in jobs:
            per_status[j.status.value] = per_status.get(j.status.value, 0) + 1
            per_agent[j.agent_name] = per_agent.get(j.agent_name, 0) + 1
        return {
            "total": len(jobs),
            "running": self._count_running(),
            "pending": len(self._pending_queue),
            "per_status": per_status,
            "per_agent": per_agent,
        }

    # ── 清理 ──

    def clear_completed(self):
        """清理已完成的任务记录"""
        finished_ids = [
            jid for jid, j in self._jobs.items()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        for jid in finished_ids:
            del self._jobs[jid]

    # ── 内部方法 ──

    def _count_running(self) -> int:
        return sum(
            1 for j in self._jobs.values()
            if j.status == JobStatus.RUNNING
        )

    def _start_job(self, job_id: str):
        """启动任务执行"""
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.PENDING:
            return

        # 创建代理实例
        agent = self._create_agent(job)
        if not agent:
            job.status = JobStatus.FAILED
            job.error_message = f"无法创建代理: {job.agent_name}"
            job.finished_at = time.time()
            self.job_finished.emit(job_id, JobStatus.FAILED.value)
            self._maybe_start_next()
            return

        # 连接信号
        agent.output_ready.connect(
            lambda text, jid=job_id: self._on_output(jid, text)
        )
        agent.error_ready.connect(
            lambda text, jid=job_id: self._on_stderr(jid, text)
        )
        agent.finished.connect(
            lambda code, status, jid=job_id: self._on_finished(jid, code, status)
        )
        agent.status_changed.connect(
            lambda s, jid=job_id: self._on_status(jid, s)
        )

        self._runners[job_id] = agent

        # 启动
        kwargs = {
            "model": job.model,
            "workdir": job.workdir,
            "thinking": job.thinking,
        }
        if job.skill and job.agent_name == "hermes":
            kwargs["skill"] = job.skill

        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        self.job_started.emit(job_id)
        self.job_progress.emit(job_id, self._job_to_dict(job))

        agent.run(job.prompt, **kwargs)

    def _create_agent(self, job: Job):
        """动态创建代理实例"""
        try:
            if job.agent_name == "opencode":
                from src.agents.opencode import OpenCodeAgent
                return OpenCodeAgent()
            elif job.agent_name == "hermes":
                from src.agents.hermes import HermesAgent
                return HermesAgent()
            elif job.agent_name == "openclaw":
                from src.agents.openclaw import OpenClawAgent
                return OpenClawAgent()
        except Exception as e:
            return None
        return None

    def _on_output(self, job_id: str, text: str):
        job = self._jobs.get(job_id)
        if job:
            job.output_lines.append(text)
            # 限制输出行数
            if len(job.output_lines) > 5000:
                job.output_lines = job.output_lines[-5000:]
        self.job_output.emit(job_id, text)

    def _on_stderr(self, job_id: str, text: str):
        self.job_error.emit(job_id, text)

    def _on_finished(self, job_id: str, exit_code: int, status: str):
        job = self._jobs.get(job_id)
        if not job:
            return

        job.exit_code = exit_code
        job.finished_at = time.time()

        if exit_code == 0:
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.FAILED
            if not job.error_message:
                job.error_message = f"退出码: {exit_code} ({status})"

        self._runners.pop(job_id, None)
        self.job_finished.emit(job_id, job.status.value)
        self.job_progress.emit(job_id, self._job_to_dict(job))

        # 启动队列中下一个任务
        self._maybe_start_next()

    def _on_status(self, job_id: str, status: str):
        job = self._jobs.get(job_id)
        if job:
            self.job_progress.emit(job_id, self._job_to_dict(job))

    def _maybe_start_next(self):
        """尝试启动队列中的下一个任务"""
        if not self._pending_queue:
            return

        running = self._count_running()
        if self.max_concurrent > 0 and running >= self.max_concurrent:
            return

        next_id = self._pending_queue.pop(0)
        self._start_job(next_id)

    def _job_to_dict(self, job: Job) -> dict:
        """将 Job 转为字典（用于信号传递）"""
        return {
            "job_id": job.job_id,
            "agent_name": job.agent_name,
            "prompt": job.prompt[:80],
            "model": job.model or "默认",
            "status": job.status.value,
            "exit_code": job.exit_code,
            "error_message": job.error_message,
            "duration": job.duration_str,
            "output_lines": len(job.output_lines),
            "created_at": job.created_at,
        }
