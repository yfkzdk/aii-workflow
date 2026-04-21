"""StateDB -- SQLite (WAL) 状态存储，替代 JSON 文件。

表结构：
- task_state: 任务主状态
- snapshots: 快照/回滚支持
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_CREATE_TASK_STATE = """
CREATE TABLE IF NOT EXISTS task_state (
    task_id        TEXT PRIMARY KEY,
    status         TEXT NOT NULL DEFAULT 'input_collecting',
    step_index     INTEGER NOT NULL DEFAULT 0,
    retry_count    INTEGER NOT NULL DEFAULT 0,
    max_retries    INTEGER NOT NULL DEFAULT 3,
    user_input_json   TEXT NOT NULL DEFAULT '{}',
    confirmation_json TEXT NOT NULL DEFAULT '{}',
    pipeline_json     TEXT NOT NULL DEFAULT '[]',
    total_input_tokens  INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_cache_hits    INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
)
"""

_CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    TEXT NOT NULL,
    state_json TEXT NOT NULL,
    label      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES task_state(task_id)
)
"""

_PIPELINE = [
    "input_collecting", "requirement_optimizing", "confirmation",
    "planning", "prompt_optimizing", "executing",
    "verifying", "archiving",
]


class StateDB:
    """SQLite WAL 模式的任务状态存储。"""

    def __init__(self, task_dir: str) -> None:
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.task_dir / "state.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    # ---- 连接管理 ----

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _ensure_tables(self) -> None:
        conn = self._connect()
        conn.execute(_CREATE_TASK_STATE)
        conn.execute(_CREATE_SNAPSHOTS)
        # 阶段三迁移：为旧表添加 token 字段
        for col, default in [
            ("total_input_tokens", 0),
            ("total_output_tokens", 0),
            ("total_cache_hits", 0),
        ]:
            try:
                conn.execute(f"ALTER TABLE task_state ADD COLUMN {col} INTEGER NOT NULL DEFAULT {default}")
            except sqlite3.OperationalError:
                pass  # 列已存在
        conn.commit()

    # ---- 核心 CRUD ----

    def init_task(self, task_id: str) -> Dict[str, Any]:
        """初始化任务，status='input_collecting'。已存在则返回现有状态。"""
        conn = self._connect()
        existing = conn.execute(
            "SELECT * FROM task_state WHERE task_id = ?", (task_id,)
        ).fetchone()
        if existing is not None:
            return self._row_to_dict(existing)

        now = datetime.now().isoformat()
        pipeline_json = json.dumps(_PIPELINE, ensure_ascii=False)
        conn.execute(
            "INSERT INTO task_state "
            "(task_id, status, step_index, retry_count, max_retries, "
            " user_input_json, confirmation_json, pipeline_json, created_at, updated_at) "
            "VALUES (?, 'input_collecting', 0, 0, 3, '{}', '{}', ?, ?, ?)",
            (task_id, pipeline_json, now, now),
        )
        conn.commit()
        print(f"[StateDB] 任务初始化: {task_id}")
        return self.get_state(task_id)

    def get_state(self, task_id: str) -> Dict[str, Any]:
        """返回任务完整状态 dict。"""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM task_state WHERE task_id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"任务不存在: {task_id}")
        return self._row_to_dict(row)

    def update_status(self, task_id: str, new_status: str,
                      next_agent: Optional[str] = None) -> Dict[str, Any]:
        """更新状态，自动计算 step_index。"""
        conn = self._connect()
        state = self.get_state(task_id)
        pipeline: List[str] = json.loads(state["pipeline_json"])

        step_index = 0
        if new_status in pipeline:
            step_index = pipeline.index(new_status)
        elif new_status in ("completed", "cancelled"):
            step_index = len(pipeline) - 1

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE task_state SET status=?, step_index=?, updated_at=? "
            "WHERE task_id=?",
            (new_status, step_index, now, task_id),
        )
        conn.commit()
        print(f"[StateDB] 状态更新: {task_id} → {new_status} (step={step_index})")
        result = self.get_state(task_id)
        result["next_agent"] = next_agent
        return result

    def save_snapshot(self, task_id: str, label: str = "") -> int:
        """持久化快照到 snapshots 表，返回快照 id。"""
        conn = self._connect()
        state = self.get_state(task_id)
        state_json = json.dumps(state, ensure_ascii=False, default=str)
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "INSERT INTO snapshots (task_id, state_json, label, created_at) "
            "VALUES (?, ?, ?, ?)",
            (task_id, state_json, label, now),
        )
        conn.commit()
        snap_id = cursor.lastrowid
        print(f"[StateDB] 快照保存: {task_id} label='{label}' id={snap_id}")
        return snap_id

    def rollback(self, task_id: str, steps: int = 1) -> bool:
        """回滚到倒数第 N 个快照。"""
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, state_json FROM snapshots WHERE task_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (task_id, steps),
        ).fetchall()

        if not rows:
            print(f"[StateDB] 回滚失败: 无快照 ({task_id})")
            return False

        # 取倒数第 N 个（即列表最后一个元素）
        target = rows[-1]
        restored = json.loads(target["state_json"])

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE task_state SET status=?, step_index=?, retry_count=?, "
            "user_input_json=?, confirmation_json=?, updated_at=? "
            "WHERE task_id=?",
            (
                restored["status"],
                restored["step_index"],
                restored["retry_count"],
                restored.get("user_input_json", "{}"),
                restored.get("confirmation_json", "{}"),
                now,
                task_id,
            ),
        )
        conn.commit()
        print(f"[StateDB] 回滚成功: {task_id} → {restored['status']} (snapshot id={target['id']})")
        return True

    def increment_retry(self, task_id: str) -> int:
        """retry_count += 1，返回新值。"""
        conn = self._connect()
        conn.execute(
            "UPDATE task_state SET retry_count = retry_count + 1, updated_at = ? "
            "WHERE task_id = ?",
            (datetime.now().isoformat(), task_id),
        )
        conn.commit()
        state = self.get_state(task_id)
        print(f"[StateDB] 重试递增: {task_id} retry_count={state['retry_count']}")
        return state["retry_count"]

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务状态。"""
        conn = self._connect()
        rows = conn.execute("SELECT * FROM task_state ORDER BY created_at").fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ---- Token 追踪（阶段三） ----

    def add_token_usage(self, task_id: str, input_tokens: int,
                        output_tokens: int, cache_hits: int) -> None:
        """累加 token 用量。"""
        conn = self._connect()
        conn.execute(
            "UPDATE task_state SET "
            "total_input_tokens = total_input_tokens + ?, "
            "total_output_tokens = total_output_tokens + ?, "
            "total_cache_hits = total_cache_hits + ?, "
            "updated_at = ? "
            "WHERE task_id = ?",
            (input_tokens, output_tokens, cache_hits,
             datetime.now().isoformat(), task_id),
        )
        conn.commit()
        state = self.get_state(task_id)
        print(f"[StateDB] Token 累加: +{input_tokens}in +{output_tokens}out | "
              f"Total: {state['total_input_tokens']}/{state['total_output_tokens']} | "
              f"Cache hits: {state['total_cache_hits']}")

    def get_token_usage(self, task_id: str) -> Dict[str, int]:
        """返回 token 用量 dict。"""
        state = self.get_state(task_id)
        return {
            "total_input_tokens": state.get("total_input_tokens", 0),
            "total_output_tokens": state.get("total_output_tokens", 0),
            "total_cache_hits": state.get("total_cache_hits", 0),
        }

    # ---- 内部工具 ----

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}