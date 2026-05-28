"""配置管理器测试"""
import sys
import os
import tempfile
import pytest

# 确保项目在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManager:
    """ConfigManager 测试套件"""

    def test_default_values(self):
        """默认配置结构正确"""
        assert "agents" in DEFAULT_CONFIG
        assert "comfyui" in DEFAULT_CONFIG
        assert "general" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["agents"]["hermes"]["enabled"] is True
        assert DEFAULT_CONFIG["comfyui"]["port"] == 8188
        assert DEFAULT_CONFIG["general"]["theme"] == "dark"

    def test_load_creates_default(self):
        """load() 在文件不存在时创建默认配置"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            tmp_path = f.name

        try:
            # 确保文件不存在
            os.unlink(tmp_path)
            cm = ConfigManager(tmp_path)
            cm.load()

            assert cm.get("agents.hermes.enabled") is True
            assert cm.get("comfyui.port") == 8188
            assert os.path.exists(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_load_existing_config(self):
        """load() 加载已有配置并合并默认值"""
        import yaml

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"general": {"theme": "light"}}, f)
            tmp_path = f.name

        try:
            cm = ConfigManager(tmp_path)
            cm.load()

            # 用户设置的值保留
            assert cm.get("general.theme") == "light"
            # 缺失的值被默认合并
            assert cm.get("agents.hermes.enabled") is True
            assert cm.get("comfyui.port") == 8188
        finally:
            os.unlink(tmp_path)

    def test_get_with_dot_path(self):
        """get() 点号路径取值"""
        cm = ConfigManager.__new__(ConfigManager)
        cm._data = DEFAULT_CONFIG.copy()

        assert cm.get("agents.hermes.enabled") is True
        assert cm.get("agents.hermes.model") == ""
        assert cm.get("comfyui.host") == "127.0.0.1"
        assert cm.get("comfyui.port") == 8188
        assert cm.get("general.font_size") == 12

    def test_get_nonexistent_key_returns_default(self):
        """get() 不存在的 key 返回 default"""
        cm = ConfigManager.__new__(ConfigManager)
        cm._data = DEFAULT_CONFIG.copy()

        assert cm.get("nonexistent.key") is None
        assert cm.get("nonexistent.key", "fallback") == "fallback"
        assert cm.get("agents.nonexistent", "nope") == "nope"

    def test_set_and_save(self):
        """set() 设置值并自动保存"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            tmp_path = f.name

        try:
            cm = ConfigManager(tmp_path)
            cm._data = DEFAULT_CONFIG.copy()

            cm.set("general.theme", "light")
            cm.set("agents.hermes.model", "claude-sonnet-4")
            cm.set("comfyui.remote_mode", True)

            # 内存中已更新
            assert cm.get("general.theme") == "light"
            assert cm.get("agents.hermes.model") == "claude-sonnet-4"
            assert cm.get("comfyui.remote_mode") is True

            # 文件已保存
            cm2 = ConfigManager(tmp_path)
            cm2.load()
            assert cm2.get("general.theme") == "light"
            assert cm2.get("agents.hermes.model") == "claude-sonnet-4"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_set_nested_new_key(self):
        """set() 创建嵌套 key"""
        cm = ConfigManager.__new__(ConfigManager)
        cm._data = {"general": {"theme": "dark"}}
        cm.config_path = None  # 避免写盘

        # 重新定义 save 避免真实写盘
        original_save = cm.save
        cm.save = lambda: None

        try:
            cm.set("general.new_key", "new_value")
            assert cm.get("general.new_key") == "new_value"

            cm.set("foo.bar.baz", 42)
            assert cm.get("foo.bar.baz") == 42
        finally:
            cm.save = original_save

    def test_merge_defaults_preserves_user_values(self):
        """_merge_defaults 保留用户已有值"""
        cm = ConfigManager.__new__(ConfigManager)
        cm._data = {"general": {"theme": "light"}}

        cm._merge_defaults(cm._data, DEFAULT_CONFIG)

        # 用户值保留
        assert cm._data["general"]["theme"] == "light"
        # 缺失的默认值被合并
        assert cm._data["general"]["font_size"] == 12
        assert "agents" in cm._data

    def test_remote_comfyui_defaults(self):
        """远程 ComfyUI 配置默认值存在"""
        assert "remote_mode" in DEFAULT_CONFIG["comfyui"]
        assert "remote_host" in DEFAULT_CONFIG["comfyui"]
        assert "api_key" in DEFAULT_CONFIG["comfyui"]
        assert DEFAULT_CONFIG["comfyui"]["remote_host"] == ""
        assert DEFAULT_CONFIG["comfyui"]["api_key"] == ""

    def test_configpath_default(self):
        """默认 config_path 指向 ~/ai-platform/config.yaml"""
        from pathlib import Path
        cm = ConfigManager()
        assert str(cm.config_path).endswith("ai-platform/config.yaml")
        assert "ai-platform" in str(cm.config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
