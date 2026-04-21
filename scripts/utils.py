"""公共工具函数"""

import json
import os
import tempfile
from pathlib import Path

from core.db import StateDB


def atomic_write_json(filepath: Path, data: dict):
    """原子写入JSON文件，防止写入中断导致数据损坏"""
    dir_p = Path(filepath).parent
    dir_p.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dir_p), suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)


def scan_workflows(workflows_dir: str) -> list:
    """扫描workflows目录下所有任务，使用StateDB读取状态"""
    wf_path = Path(workflows_dir)
    if not wf_path.exists():
        return []

    tasks = []
    for task_dir in sorted(wf_path.iterdir()):
        if not task_dir.is_dir():
            continue
        db_file = task_dir / "state.db"
        if not db_file.exists():
            continue

        try:
            db = StateDB(str(task_dir))
            # task_id 从目录名推导（StateDB 可能尚未 init）
            task_id = task_dir.name
            try:
                state = db.get_state(task_id)
            except ValueError:
                continue
            tasks.append({
                "task_id": state.get("task_id", task_id),
                "status": state.get("status", "unknown"),
                "pipeline": json.loads(state.get("pipeline_json", "[]")),
                "step_index": state.get("step_index", 0),
                "created_at": state.get("created_at", ""),
                "updated_at": state.get("updated_at", ""),
                "dir": str(task_dir)
            })
            db.close()
        except Exception:
            continue

    return tasks


def format_status_line(task: dict) -> str:
    """格式化单个任务的状态行"""
    task_id = task.get("task_id", "?")
    status = task.get("status", "unknown")
    step_idx = task.get("step_index", 0)
    pipeline = task.get("pipeline", [])
    if isinstance(pipeline, str):
        try:
            pipeline = json.loads(pipeline)
        except (json.JSONDecodeError, TypeError):
            pipeline = []
    updated = task.get("updated_at", "")

    current_step = pipeline[step_idx] if 0 <= step_idx < len(pipeline) else ("cancelled" if status == "cancelled" else "?")
    progress = f"{step_idx}/{len(pipeline)}" if pipeline else "?"
    time_str = updated[:16] if updated else ""

    status_icons = {
        "completed": "✓",
        "executing": "▶",
        "planning": "◎",
        "input_collecting": "✎",
        "requirement_optimizing": "⚡",
        "confirmation": "⏸",
        "prompt_optimizing": "✍",
        "verifying": "🔍",
        "archiving": "📦",
        "cancelled": "✗",
    }
    icon = status_icons.get(status, "·")

    return f"  {icon} {task_id[:30]:<30} {status:<25} {progress:>5} {time_str}"


def setup_encoding():
    """设置UTF-8编码环境"""
    import sys
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')