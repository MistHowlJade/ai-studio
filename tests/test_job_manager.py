"""任务管理测试（纯 Python 层 — Job + JobStatus 数据类）

注意：JobManager 继承 QObject，需要 QApplication 上下文，
无法在无头环境测试。本文件只测试数据模型和纯逻辑部分。
"""
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.jobs.job_manager import Job, JobStatus


class TestJobStatus:
    """JobStatus 枚举测试"""

    def test_all_statuses_exist(self):
        """所有状态枚举存在"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_status_equality(self):
        """状态比较"""
        assert JobStatus.PENDING == JobStatus.PENDING
        assert JobStatus.RUNNING != JobStatus.COMPLETED


class TestJob:
    """Job 数据类测试"""

    def test_job_defaults(self):
        """默认值正确"""
        job = Job(job_id="abc123", agent_name="hermes", prompt="test")

        assert job.job_id == "abc123"
        assert job.agent_name == "hermes"
        assert job.prompt == "test"
        assert job.model is None
        assert job.workdir is None
        assert job.skill is None
        assert job.thinking is False
        assert job.status == JobStatus.PENDING
        assert job.exit_code is None
        assert job.error_message is None
        assert job.started_at is None
        assert job.finished_at is None
        assert job.output_lines == []

    def test_job_with_all_fields(self):
        """完整字段赋值"""
        job = Job(
            job_id="x1",
            agent_name="opencode",
            prompt="write code",
            model="claude-sonnet-4",
            workdir="/home/user/project",
            skill="python-tdd",
            thinking=True,
        )

        assert job.model == "claude-sonnet-4"
        assert job.workdir == "/home/user/project"
        assert job.skill == "python-tdd"
        assert job.thinking is True

    def test_duration_unstarted(self):
        """未开始的 job duration 为 0"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        assert job.duration == 0

    def test_duration_running(self):
        """运行中的 job duration > 0"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.started_at = time.time() - 5  # 5 秒前开始
        assert job.duration >= 5

    def test_duration_finished(self):
        """已完成的 job duration"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.started_at = 1000.0
        job.finished_at = 1010.0
        assert job.duration == 10.0

    def test_duration_str_seconds(self):
        """duration_str 秒级"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.started_at = 1000.0
        job.finished_at = 1003.5
        assert "s" in job.duration_str

    def test_duration_str_minutes(self):
        """duration_str 分钟级"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.started_at = 1000.0
        job.finished_at = 1120.0  # 120s = 2m
        assert "m" in job.duration_str

    def test_duration_str_hours(self):
        """duration_str 小时级"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.started_at = 1000.0
        job.finished_at = 4600.0  # 3600s = 1h
        assert "h" in job.duration_str

    def test_output_lines_append(self):
        """输出行累积"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        job.output_lines.append("line 1")
        job.output_lines.append("line 2")
        assert len(job.output_lines) == 2
        assert job.output_lines == ["line 1", "line 2"]

    def test_status_transition(self):
        """状态转换"""
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        assert job.status == JobStatus.PENDING

        job.status = JobStatus.RUNNING
        assert job.status == JobStatus.RUNNING

        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED

    def test_created_at_auto_set(self):
        """created_at 自动设置"""
        now = time.time()
        job = Job(job_id="a", agent_name="hermes", prompt="test")
        assert abs(job.created_at - now) < 2  # 2 秒内


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
