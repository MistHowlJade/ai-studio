"""OpenCode 代理 — opencode CLI 完整封装"""
from src.agents.base import BaseAgent


class OpenCodeAgent(BaseAgent):
    """OpenCode CLI 代理 — 支持 thinking 模式、工作目录、权限模式

    用法：
        agent = OpenCodeAgent()
        agent.run("写一个 REST API", model="claude-sonnet-4",
                   thinking=True, workdir="/path/to/project")
    """

    def run(
        self,
        prompt: str,
        model: str | None = None,
        workdir: str | None = None,
        thinking: bool = False,
        permission_mode: str | None = None,
        **kwargs,
    ):
        """构建并执行 opencode 命令

        Args:
            prompt: 任务描述
            model: 模型名称
            workdir: 工作目录
            thinking: 启用思考模式（--thinking）
            permission_mode: 权限模式（'acceptEdits' | 'bypassPermissions' | 'plan' | 'default'）
        """
        cmd = ["opencode", "run"]

        if model:
            cmd.extend(["--model", model])

        if thinking:
            cmd.append("--thinking")

        if permission_mode:
            cmd.extend(["--permission-mode", permission_mode])

        cmd.append(prompt)

        self._start_process(cmd, workdir=workdir)

    # ── 便捷方法 ──

    def plan_only(self, prompt: str, workdir: str | None = None,
                  model: str | None = None):
        """仅生成计划，不执行"""
        self.run(prompt, model=model, workdir=workdir,
                 permission_mode="plan", thinking=True)

    def auto_accept(self, prompt: str, workdir: str | None = None,
                    model: str | None = None):
        """自动接受编辑，无需确认"""
        self.run(prompt, model=model, workdir=workdir,
                 permission_mode="acceptEdits", thinking=True)
