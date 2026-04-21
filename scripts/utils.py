"""公共工具函数"""

import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(filepath: Path, data: dict):
    """原子写入JSON文件，防止写入中断导致数据损坏"""
    dir_p = Path(filepath).parent
    dir_p.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dir_p), suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)


def scan_workflows(workflows_dir: str) -> list:
    """扫描workflows目录下所有任务，返回状态列表"""
    wf_path = Path(workflows_dir)
    if not wf_path.exists():
        return []

    tasks = []
    for task_dir in sorted(wf_path.iterdir()):
        if not task_dir.is_dir():
            continue
        state_file = task_dir / "state.json"
        if not state_file.exists():
            continue

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            tasks.append({
                "task_id": state.get("task_id", task_dir.name),
                "status": state.get("status", "unknown"),
                "pipeline": state.get("pipeline", []),
                "step_index": state.get("current_step_index", 0),
                "created_at": state.get("created_at", ""),
                "updated_at": state.get("updated_at", ""),
                "dir": str(task_dir)
            })
        except (json.JSONDecodeError, OSError):
            continue

    return tasks


def format_status_line(task: dict) -> str:
    """格式化单个任务的状态行"""
    task_id = task.get("task_id", "?")
    status = task.get("status", "unknown")
    step_idx = task.get("step_index", 0)
    pipeline = task.get("pipeline", [])
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