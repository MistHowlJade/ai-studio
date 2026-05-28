"""启动诊断 — 检测代理 CLI 可用性 + ComfyUI 状态"""
import shutil
import requests
from dataclasses import dataclass


@dataclass
class DepCheck:
    """单个依赖检测结果"""
    name: str
    available: bool
    version: str = ""
    error: str = ""


AGENT_CHECKS = {
    "hermes": {"cmd": "hermes", "args": ["--version"]},
    "opencode": {"cmd": "opencode", "args": ["--version"]},
    "openclaw": {"cmd": "openclaw", "args": ["--version"]},
}


def check_cli(command: str) -> bool:
    """检测 CLI 是否在 PATH 中"""
    return shutil.which(command) is not None


def check_agent_cli(agent_name: str) -> DepCheck:
    """检测单个代理 CLI"""
    info = AGENT_CHECKS.get(agent_name)
    if not info:
        return DepCheck(name=agent_name, available=False, error="未知代理")

    cmd = info["cmd"]
    if not check_cli(cmd):
        return DepCheck(
            name=agent_name,
            available=False,
            error=f"{cmd} 未安装或不在 PATH 中",
        )

    return DepCheck(name=agent_name, available=True, version=cmd)


def check_comfy_cli() -> DepCheck:
    """检测 comfy CLI"""
    if check_cli("comfy"):
        return DepCheck(name="comfy", available=True, version="comfy")
    return DepCheck(
        name="comfy",
        available=False,
        error="comfy CLI 未安装（不影响远程模式）",
    )


def check_comfyui_server(host: str = "127.0.0.1", port: int = 8188) -> DepCheck:
    """检测 ComfyUI 服务是否可达"""
    try:
        r = requests.get(
            f"http://{host}:{port}/system_stats", timeout=3
        )
        if r.status_code == 200:
            return DepCheck(
                name="comfyui_server",
                available=True,
                version=f"{host}:{port}",
            )
        return DepCheck(
            name="comfyui_server",
            available=False,
            error=f"服务响应异常: HTTP {r.status_code}",
        )
    except requests.ConnectionError:
        return DepCheck(
            name="comfyui_server",
            available=False,
            error=f"无法连接 {host}:{port}",
        )
    except Exception as e:
        return DepCheck(
            name="comfyui_server",
            available=False,
            error=str(e),
        )


def run_diagnostics(config) -> dict:
    """运行完整诊断，返回所有检测结果

    Returns:
        {
            "agents": {agent_name: DepCheck, ...},
            "comfy_cli": DepCheck,
            "comfyui_server": DepCheck,
            "all_agents_ok": bool,
            "summary": str,
        }
    """
    # 代理 CLI 检测
    agents = {}
    for agent_name in AGENT_CHECKS:
        agents[agent_name] = check_agent_cli(agent_name)

    # Comfy CLI
    comfy_cli = check_comfy_cli()

    # ComfyUI 服务
    host = config.get("comfyui.host", "127.0.0.1")
    port = config.get("comfyui.port", 8188)
    comfyui_srv = check_comfyui_server(host, port)

    all_agents_ok = all(a.available for a in agents.values())

    # 生成摘要
    lines = ["=== AI Studio 启动诊断 ==="]
    for name, dep in agents.items():
        icon = "✅" if dep.available else "❌"
        lines.append(f"  {icon} {name}: {dep.version or dep.error}")

    icon = "✅" if comfy_cli.available else "⚠️"
    lines.append(f"  {icon} comfy CLI: {comfy_cli.version or comfy_cli.error}")

    icon = "✅" if comfyui_srv.available else "⚪"
    lines.append(f"  {icon} ComfyUI: {comfyui_srv.version or comfyui_srv.error}")

    return {
        "agents": agents,
        "comfy_cli": comfy_cli,
        "comfyui_server": comfyui_srv,
        "all_agents_ok": all_agents_ok,
        "summary": "\n".join(lines),
    }
