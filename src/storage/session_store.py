"""会话存储 — SQLite 多轮对话线程 + 全文搜索 + 历史浏览"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone


class SessionStore:
    """SQLite 会话历史存储 — 多轮对话线程

    表结构：
        threads: 对话线程 (id, title, agent, model, message_count, created_at, updated_at)
        messages: 消息 (id, thread_id, role, content, metadata_json, created_at)
    """

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path.home() / "ai-platform" / "sessions.db"
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '(新对话)',
                agent TEXT NOT NULL,
                model TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now')),
                updated_at TIMESTAMP DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
                content TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT (datetime('now')),
                FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_thread
                ON messages(thread_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_threads_agent
                ON threads(agent);
            CREATE INDEX IF NOT EXISTS idx_threads_updated
                ON threads(updated_at DESC);
        """)
        self.conn.commit()

    # ── 线程操作 ──

    def create_thread(
        self, agent: str, title: str = None, model: str = ""
    ) -> int:
        """创建新对话线程，返回 thread_id"""
        if title is None:
            title = f"{agent} 对话 - {datetime.now().strftime('%m/%d %H:%M')}"

        cursor = self.conn.execute(
            "INSERT INTO threads (title, agent, model) VALUES (?, ?, ?)",
            (title, agent, model),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_thread(self, thread_id: int) -> dict | None:
        """获取线程信息"""
        row = self.conn.execute(
            "SELECT * FROM threads WHERE id = ?", (thread_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None

    def list_threads(
        self, agent: str = None, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """列出对话线程（按最近更新排序）"""
        query = "SELECT * FROM threads"
        params = []
        if agent:
            query += " WHERE agent = ?"
            params.append(agent)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_thread_title(self, thread_id: int, title: str):
        """更新线程标题"""
        self.conn.execute(
            "UPDATE threads SET title = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (title, thread_id),
        )
        self.conn.commit()

    def delete_thread(self, thread_id: int):
        """删除线程及其所有消息"""
        self.conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        self.conn.commit()

    # ── 消息操作 ──

    def add_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        metadata: dict = None,
    ) -> int:
        """添加消息到线程，返回 message_id"""
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        cursor = self.conn.execute(
            "INSERT INTO messages (thread_id, role, content, metadata_json) "
            "VALUES (?, ?, ?, ?)",
            (thread_id, role, content, meta_json),
        )

        # 更新线程计数和时间
        self.conn.execute(
            "UPDATE threads SET message_count = message_count + 1, "
            "updated_at = datetime('now') WHERE id = ?",
            (thread_id,),
        )

        # 自动设置标题（用第一条用户消息）
        thread = self.get_thread(thread_id)
        if thread and thread["title"].startswith("(新对话)") or \
           thread and thread["message_count"] <= 2:
            if role == "user" and len(content) > 0:
                title = content[:60] + ("..." if len(content) > 60 else "")
                self.update_thread_title(thread_id, title)

        self.conn.commit()
        return cursor.lastrowid

    def get_messages(
        self, thread_id: int, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """获取线程消息列表"""
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE thread_id = ? "
            "ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (thread_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(
        self, thread_id: int, max_turns: int = 50
    ) -> list[dict]:
        """获取完整对话（user + assistant 对），用于多轮上下文"""
        rows = self.conn.execute(
            "SELECT role, content FROM messages "
            "WHERE thread_id = ? AND role IN ('user', 'assistant') "
            "ORDER BY created_at ASC LIMIT ?",
            (thread_id, max_turns * 2),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 搜索 ──

    def search(
        self,
        query: str,
        agent: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """全文搜索消息内容（LIKE 匹配）"""
        q = "SELECT m.*, t.title as thread_title, t.agent as thread_agent " \
            "FROM messages m JOIN threads t ON m.thread_id = t.id " \
            "WHERE m.content LIKE ?"
        params = [f"%{query}%"]

        if agent:
            q += " AND t.agent = ?"
            params.append(agent)

        q += " ORDER BY m.created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def search_threads(
        self, query: str, agent: str = None, limit: int = 10
    ) -> list[dict]:
        """搜索线程标题"""
        q = "SELECT * FROM threads WHERE title LIKE ?"
        params = [f"%{query}%"]

        if agent:
            q += " AND agent = ?"
            params.append(agent)

        q += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # ── 统计 ──

    def get_recent_activity(self, limit: int = 10) -> list[dict]:
        """获取最近活跃线程摘要（用于首页展示）"""
        rows = self.conn.execute(
            "SELECT t.id, t.title, t.agent, t.model, t.updated_at, "
            "(SELECT content FROM messages WHERE thread_id = t.id "
            " AND role = 'user' ORDER BY created_at DESC LIMIT 1) "
            "as last_prompt "
            "FROM threads t ORDER BY t.updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """获取存储统计"""
        threads = self.conn.execute(
            "SELECT COUNT(*) as count FROM threads"
        ).fetchone()["count"]
        messages = self.conn.execute(
            "SELECT COUNT(*) as count FROM messages"
        ).fetchone()["count"]
        per_agent = self.conn.execute(
            "SELECT agent, COUNT(*) as count FROM threads "
            "GROUP BY agent ORDER BY count DESC"
        ).fetchall()
        return {
            "threads": threads,
            "messages": messages,
            "per_agent": {r["agent"]: r["count"] for r in per_agent},
        }

    # ── 兼容旧 API ──

    def save(self, agent, prompt, response, model=""):
        """兼容旧的单次保存 API — 创建临时线程"""
        tid = self.create_thread(agent, model=model)
        self.add_message(tid, "user", prompt)
        self.add_message(tid, "assistant", response)
        return tid

    def get_recent(self, agent=None, limit=10):
        """兼容旧的获取最近 API"""
        activity = self.get_recent_activity(limit)
        result = []
        for a in activity:
            if agent and a["agent"] != agent:
                continue
            result.append({
                "agent": a["agent"],
                "prompt": a.get("last_prompt", ""),
                "time": a["updated_at"],
                "thread_id": a["id"],
                "title": a["title"],
            })
        return result

    def get_history(self, agent=None, limit=50):
        return self.get_recent(agent, limit)

    # ── 生命周期 ──

    def close(self):
        self.conn.close()

    def vacuum(self):
        """数据库压缩优化"""
        self.conn.execute("VACUUM")
