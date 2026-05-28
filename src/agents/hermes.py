"""Hermes 代理 — hermes CLI 完整封装"""
from src.agents.base import BaseAgent


class HermesAgent(BaseAgent):
    """Hermes CLI 代理 — 支持 skill、thinking 模式、工作目录

    用法：
        agent = HermesAgent()
        agent.run("重构 auth 模块", model="claude-sonnet-4",
                   skill="code-review", thinking=True,
                   workdir="/path/to/project")
    """

    def run(
        self,
        prompt: str,
        model: str | None = None,
        workdir: str | None = None,
        skill: str | None = None,
        thinking: bool = False,
        quiet: bool = True,  # -q 标志，非交互模式
        **kwargs,
    ):
        """构建并执行 hermes 命令

        Args:
            prompt: 任务描述
            model: 模型名称（如 'claude-sonnet-4'）
            workdir: 工作目录
            skill: 技能名称（对应 -s 参数）
            thinking: 启用思考模式（--thinking）
            quiet: 非交互模式（-q 标志）
        """
        cmd = ["hermes"]

        if quiet:
            cmd.append("chat")
            cmd.append("-q")
        else:
            cmd.append("chat")

        if model:
            cmd.extend(["--model", model])

        if thinking:
            cmd.append("--thinking")

        if skill:
            cmd.extend(["-s", skill])

        cmd.append(prompt)

        self._start_process(cmd, workdir=workdir)

    # ── 便捷方法 ──

    def code_review(self, file_path: str, workdir: str | None = None,
                    model: str | None = None):
        """快速代码审查"""
        self.run(
            f"Review {file_path} for bugs, security issues, and code quality",
            model=model, workdir=workdir, skill="code-review"
        )

    def write_code(self, prompt: str, workdir: str | None = None,
                   model: str | None = None):
        """快速编码任务"""
        self.run(prompt, model=model, workdir=workdir, thinking=True)
