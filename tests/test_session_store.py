"""会话存储测试"""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.storage.session_store import SessionStore


class TestSessionStore:
    """SessionStore 测试套件"""

    @pytest.fixture
    def store(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = SessionStore(path)
        yield store
        store.close()
        if os.path.exists(path):
            os.unlink(path)

    # ── 线程操作 ──

    def test_create_thread(self, store):
        """创建对话线程"""
        tid = store.create_thread("hermes", title="测试对话")
        assert tid > 0

        thread = store.get_thread(tid)
        assert thread["title"] == "测试对话"
        assert thread["agent"] == "hermes"
        assert thread["message_count"] == 0

    def test_create_thread_default_title(self, store):
        """默认标题"""
        tid = store.create_thread("opencode")
        thread = store.get_thread(tid)
        assert "opencode" in thread["title"]

    def test_list_threads(self, store):
        """列出线程"""
        store.create_thread("hermes", title="A")
        store.create_thread("opencode", title="B")
        store.create_thread("hermes", title="C")

        all_threads = store.list_threads()
        assert len(all_threads) == 3

        hermes_threads = store.list_threads(agent="hermes")
        assert len(hermes_threads) == 2

        # 所有三个线程都存在
        titles = {t["title"] for t in all_threads}
        assert titles == {"A", "B", "C"}

    def test_update_thread_title(self, store):
        """更新标题"""
        tid = store.create_thread("hermes", title="旧标题")
        store.update_thread_title(tid, "新标题")
        thread = store.get_thread(tid)
        assert thread["title"] == "新标题"

    def test_delete_thread_cascades(self, store):
        """删除线程级联删除消息"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "hello")

        store.delete_thread(tid)
        assert store.get_thread(tid) is None
        assert len(store.get_messages(tid)) == 0

    # ── 消息操作 ──

    def test_add_message(self, store):
        """添加消息"""
        tid = store.create_thread("hermes")
        mid = store.add_message(tid, "user", "你好", metadata={"model": "claude"})
        assert mid > 0

        thread = store.get_thread(tid)
        assert thread["message_count"] == 1

    def test_add_message_updates_title(self, store):
        """第一条用户消息自动设标题"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "帮我写一个排序算法")

        thread = store.get_thread(tid)
        assert "排序算法" in thread["title"]

    def test_get_messages(self, store):
        """获取消息列表"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "Q1")
        store.add_message(tid, "assistant", "A1")
        store.add_message(tid, "user", "Q2")

        msgs = store.get_messages(tid)
        assert len(msgs) == 3
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Q1"
        assert msgs[2]["content"] == "Q2"

    def test_get_conversation(self, store):
        """获取完整对话上下文"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "Q1")
        store.add_message(tid, "assistant", "A1")
        store.add_message(tid, "system", "note")  # 应该被过滤
        store.add_message(tid, "user", "Q2")
        store.add_message(tid, "assistant", "A2")

        conv = store.get_conversation(tid)
        assert len(conv) == 4  # 只有 user + assistant
        assert conv[0]["content"] == "Q1"
        assert conv[-1]["content"] == "A2"

    def test_get_conversation_max_turns(self, store):
        """对话轮数限制"""
        tid = store.create_thread("hermes")
        for i in range(10):
            store.add_message(tid, "user", f"Q{i}")
            store.add_message(tid, "assistant", f"A{i}")

        conv = store.get_conversation(tid, max_turns=3)
        assert len(conv) == 6  # 3 turns × 2 messages

    def test_message_pagination(self, store):
        """消息分页"""
        tid = store.create_thread("hermes")
        for i in range(10):
            store.add_message(tid, "user", f"msg_{i}")

        msgs = store.get_messages(tid, limit=3, offset=5)
        assert len(msgs) == 3
        assert msgs[0]["content"] == "msg_5"

    # ── 搜索 ──

    def test_search(self, store):
        """全文搜索"""
        tid = store.create_thread("hermes", title="Python 开发")
        # 先加消息触发自动标题（覆盖原标题）
        store.add_message(tid, "user", "如何用 pandas 分析数据")
        store.add_message(tid, "assistant", "使用 read_csv 读取文件")

        results = store.search("pandas")
        assert len(results) >= 1
        # thread_title 被 add_message 自动设为第一条用户消息
        assert "pandas" in results[0]["thread_title"]

    def test_search_no_results(self, store):
        """无结果搜索"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "hello")

        results = store.search("zzzz_not_found")
        assert len(results) == 0

    def test_search_filtered_by_agent(self, store):
        """按代理过滤搜索"""
        tid1 = store.create_thread("hermes")
        store.add_message(tid1, "user", "hermes chat")

        tid2 = store.create_thread("opencode")
        store.add_message(tid2, "user", "opencode chat")

        results = store.search("chat", agent="opencode")
        assert len(results) == 1
        assert results[0]["thread_agent"] == "opencode"

    def test_search_threads(self, store):
        """搜索线程标题"""
        store.create_thread("hermes", title="数据分析")
        store.create_thread("opencode", title="前端开发")

        results = store.search_threads("数据")
        assert len(results) == 1
        assert "数据" in results[0]["title"]

    # ── 统计 ──

    def test_get_stats_empty(self, store):
        """空数据库统计"""
        stats = store.get_stats()
        assert stats["threads"] == 0
        assert stats["messages"] == 0

    def test_get_stats(self, store):
        """有数据时统计"""
        tid1 = store.create_thread("hermes")
        store.add_message(tid1, "user", "Q1")
        store.add_message(tid1, "assistant", "A1")

        tid2 = store.create_thread("opencode")
        store.add_message(tid2, "user", "Q2")

        stats = store.get_stats()
        assert stats["threads"] == 2
        assert stats["messages"] == 3
        assert stats["per_agent"]["hermes"] == 1
        assert stats["per_agent"]["opencode"] == 1

    def test_get_recent_activity(self, store):
        """最近活跃线程"""
        tid = store.create_thread("hermes")
        store.add_message(tid, "user", "new question")

        activity = store.get_recent_activity()
        assert len(activity) == 1
        assert activity[0]["agent"] == "hermes"
        assert activity[0]["last_prompt"] == "new question"

    # ── 兼容 API ──

    def test_save_legacy_api(self, store):
        """旧的 save() API"""
        tid = store.save("hermes", "hello", "world", model="claude")
        assert tid > 0

        msgs = store.get_messages(tid)
        assert len(msgs) == 2
        assert msgs[0]["content"] == "hello"
        assert msgs[1]["content"] == "world"

    def test_get_recent_legacy_api(self, store):
        """旧的 get_recent() API"""
        store.save("hermes", "Q1", "A1")
        store.save("opencode", "Q2", "A2")

        recent = store.get_recent()
        assert len(recent) == 2

        recent_hermes = store.get_recent(agent="hermes")
        assert len(recent_hermes) == 1

    def test_get_history_alias(self, store):
        """get_history 是 get_recent 的别名"""
        store.save("hermes", "test", "ok")
        assert len(store.get_history()) == 1

    # ── 角色校验 ──

    def test_invalid_role_rejected(self, store):
        """非法角色被 SQL CHECK 拒绝"""
        tid = store.create_thread("hermes")
        with pytest.raises(Exception):
            store.add_message(tid, "invalid_role", "test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
