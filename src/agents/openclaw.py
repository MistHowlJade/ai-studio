"""OpenClaw 代理 — openclaw CLI 完整封装"""
from src.agents.base import BaseAgent


class OpenClawAgent(BaseAgent):
    """OpenClaw CLI 代理 — 支持模型、工作目录、上下文目录

    用法：
        agent = OpenClawAgent()
        agent.run("分析项目结构", model="claude-sonnet-4",
                   workdir="/path/to/project")

    注意：如果已通过 'hermes claw migrate' 迁移到 Hermes，
          OpenClaw 二进制可能不存在。启动检测会提示此情况。
    """

    def run(
        self,
        prompt: str,
        model: str | None = None,
        workdir: str | None = None,
        context_dir: str | None = None,
        **kwargs,
    ):
        """构建并执行 openclaw 命令

        Args:
            prompt: 任务描述
            model: 模型名称
            workdir: 工作目录
            context_dir: 额外上下文目录
        """
        cmd = ["openclaw", "run"]

        if model:
            cmd.extend(["--model", model])

        if context_dir:
            cmd.extend(["--context-dir", context_dir])

        cmd.append(prompt)

        self._start_process(cmd, workdir=workdir)
