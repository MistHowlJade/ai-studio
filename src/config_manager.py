"""配置管理器 — 读写 config.yaml，支持点号路径访问"""
import os
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "agents": {
        "opencode": {"enabled": True, "model": ""},
        "hermes": {"enabled": True, "model": ""},
        "openclaw": {"enabled": True, "model": ""},
    },
    "comfyui": {
        "host": "127.0.0.1",
        "port": 8188,
        "workspace": "~/comfy/ComfyUI",
        "auto_start": False,
        "remote_mode": False,
        "remote_host": "",
        "api_key": "",
    },
    "general": {
        "theme": "dark",
        "font_size": 12,
        "max_history": 1000,
        "follow_system_theme": True,
    },
}


class ConfigManager:
    """配置管理器，自动从 ~/ai-platform/config.yaml 加载"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = Path.home() / "ai-platform" / "config.yaml"
        self.config_path = Path(config_path)
        self._data = {}

    def load(self):
        """加载配置，如果文件不存在则创建默认配置"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
            # 合并缺失的默认值
            self._merge_defaults(self._data, DEFAULT_CONFIG)
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def get(self, key, default=None):
        """点号路径取值，如 get('agents.hermes.model')"""
        keys = key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
                if node is None:
                    return default
            else:
                return default
        return node

    def set(self, key, value):
        """点号路径设置值并自动保存"""
        keys = key.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self.save()

    @property
    def data(self):
        return self._data

    def _merge_defaults(self, target, defaults):
        """递归合并默认配置到目标"""
        for key, value in defaults.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._merge_defaults(target[key], value)
