"""进度追踪器 — 任务DAG状态管理和进度查询"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from utils import atomic_write_json


class ProgressTracker:
    """任务进度追踪：DAG状态、进度百分比、可执行任务"""

    def __init__(self, task_dir: str):
        self.task_dir = Path(task_dir)
        self.state_file = self.task_dir / "state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """加载state.json"""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        """保存state.json"""
        self.state["updated_at"] = datetime.now().isoformat()
        atomic_write_json(self.state_file, self.state)

    def init_dag(self, tasks: List[Dict]):
        """初始化任务DAG"""
        task_dag = {
            "tasks": [],
            "progress": {
                "total_tasks": len(tasks),
                "completed_tasks": 0,
                "percentage": 0,
                "current_task": None,
                "blocked_tasks": [],
                "eta_seconds": None
            }
        }

        for task in tasks:
            task_entry = {
                "id": task.get("id"),
                "name": task.get("name", task.get("id")),
                "dependencies": task.get("dependencies", []),
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "substeps": []
            }
            task_dag["tasks"].append(task_entry)

        self.state["task_dag"] = task_dag
        self._save_state()
        return task_dag

    def get_progress(self) -> dict:
        """获取当前进度摘要"""
        dag = self.state.get("task_dag", {})
        tasks = dag.get("tasks", [])

        if not tasks:
            return {
                "total": 0,
                "completed": 0,
                "percentage": 0,
                "current_task": None,
                "blocked_tasks": []
            }

        completed = sum(1 for t in tasks if t.get("status") == "completed")
        total = len(tasks)
        in_progress = next((t for t in tasks if t.get("status") == "in_progress"), None)

        return {
            "total": total,
            "completed": completed,
            "percentage": round(completed / total * 100) if total else 0,
            "current_task": in_progress["id"] if in_progress else None,
            "blocked_tasks": self._get_blocked(tasks),
            "eta_seconds": dag.get("progress", {}).get("eta_seconds")
        }

    def _get_blocked(self, tasks: List[Dict]) -> List[Dict]:
        """找出被阻塞的任务（依赖未完成）"""
        completed_ids = {t["id"] for t in tasks if t.get("status") == "completed"}
        blocked = []

        for t in tasks:
            if t.get("status") == "pending":
                missing_deps = [d for d in t.get("dependencies", []) if d not in completed_ids]
                if missing_deps:
                    blocked.append({
                        "id": t["id"],
                        "name": t.get("name", t["id"]),
                        "waiting_for": missing_deps
                    })

        return blocked

    def update_task(self, task_id: str, status: str, substeps: List[Dict] = None):
        """更新单个任务状态"""
        tasks = self.state.get("task_dag", {}).get("tasks", [])
        task_found = False

        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = status
                task_found = True

                if status == "in_progress":
                    task["started_at"] = datetime.now().isoformat()
                elif status in ("completed", "failed"):
                    task["completed_at"] = datetime.now().isoformat()

                if substeps:
                    task["substeps"] = substeps

                break

        if not task_found:
            print(f"[WARN] 任务未找到: {task_id}")
            return {"error": f"task_not_found: {task_id}", "available_ids": [t.get("id") for t in tasks]}

        self._update_progress_summary()
        self._save_state()
        return {"status": "updated", "task_id": task_id, "new_status": status}

    def _update_progress_summary(self):
        """更新进度摘要"""
        tasks = self.state.get("task_dag", {}).get("tasks", [])
        if not tasks:
            return

        completed = sum(1 for t in tasks if t.get("status") == "completed")
        total = len(tasks)
        in_progress = next((t for t in tasks if t.get("status") == "in_progress"), None)

        if "task_dag" not in self.state:
            self.state["task_dag"] = {}
        if "progress" not in self.state["task_dag"]:
            self.state["task_dag"]["progress"] = {}

        self.state["task_dag"]["progress"].update({
            "total_tasks": total,
            "completed_tasks": completed,
            "percentage": round(completed / total * 100) if total else 0,
            "current_task": in_progress["id"] if in_progress else None,
            "blocked_tasks": self._get_blocked(tasks)
        })

    def get_executable_tasks(self) -> List[Dict]:
        """获取可执行的任务（依赖已满足且未开始）"""
        tasks = self.state.get("task_dag", {}).get("tasks", [])
        completed_ids = {t["id"] for t in tasks if t.get("status") == "completed"}

        executable = []
        for t in tasks:
            if t.get("status") == "pending":
                deps = t.get("dependencies", [])
                deps_met = all(d in completed_ids for d in deps)
                if deps_met:
                    executable.append({
                        "id": t["id"],
                        "name": t.get("name", t["id"]),
                        "dependencies": deps
                    })

        return executable

    def get_parallel_groups(self) -> List[List[Dict]]:
        """获取可并行执行的任务分组"""
        tasks = self.state.get("task_dag", {}).get("tasks", [])
        if not tasks:
            return []

        task_map = {t["id"]: t for t in tasks}
        groups = []
        assigned = set()

        while len(assigned) < len(tasks):
            group = []
            for t in tasks:
                if t["id"] in assigned:
                    continue
                deps = t.get("dependencies", [])
                if all(d in assigned for d in deps):
                    group.append({"id": t["id"], "name": t.get("name", t["id"])})

            if not group:
                break

            groups.append(group)
            assigned.update(t["id"] for t in group)

        return groups

    def report_progress(self) -> str:
        """生成人类可读的进度报告"""
        progress = self.get_progress()
        lines = [
            f"总进度: {progress['completed']}/{progress['total']} ({progress['percentage']}%)",
        ]

        if progress.get("current_task"):
            lines.append(f"当前任务: {progress['current_task']}")

        blocked = progress.get("blocked_tasks", [])
        if blocked:
            lines.append(f"阻塞任务: {', '.join(b['id'] for b in blocked)}")

        return "\n".join(lines)

    def export_dag_visualization(self) -> str:
        """生成Mermaid DAG可视化"""
        tasks = self.state.get("task_dag", {}).get("tasks", [])
        if not tasks:
            return "graph LR\n  空"

        lines = ["graph LR"]

        for t in tasks:
            status = t.get("status", "pending")
            style = {"pending": ":::pending", "in_progress": ":::running",
                     "completed": ":::done", "failed": ":::failed"}.get(status, "")
            lines.append(f"  {t['id']}[{t.get('name', t['id'])}]{style}")

        for t in tasks:
            for dep in t.get("dependencies", []):
                lines.append(f"  {dep} --> {t['id']}")

        lines.extend([
            "  classDef pending fill:#ccc,stroke:#666",
            "  classDef running fill:#f90,stroke:#c60",
            "  classDef done fill:#9c6,stroke:#693",
            "  classDef failed fill:#f66,stroke:#c33"
        ])

        return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  status <task_dir>     - Show progress")
        print("  executable <task_dir> - List executable tasks")
        print("  update <task_dir> <task_id> <status> - Update task")
        print("  groups <task_dir>     - Show parallel groups")
        print("  init <task_dir> <tasks_json> - Initialize DAG")
        print("  report <task_dir>     - Human-readable report")
        print("  visualize <task_dir>  - Mermaid DAG")
        sys.exit(0)

    cmd, *args = sys.argv[1:]

    if cmd == "status":
        task_dir = args[0]
        tracker = ProgressTracker(task_dir)
        progress = tracker.get_progress()
        print(json.dumps(progress, ensure_ascii=False, indent=2))

    elif cmd == "executable":
        task_dir = args[0]
        tracker = ProgressTracker(task_dir)
        tasks = tracker.get_executable_tasks()
        print(json.dumps({"executable_tasks": tasks}, ensure_ascii=False, indent=2))

    elif cmd == "update":
        task_dir = args[0]
        task_id = args[1]
        status = args[2]
        tracker = ProgressTracker(task_dir)
        tracker.update_task(task_id, status)
        print(json.dumps({"status": "updated", "task_id": task_id, "new_status": status}))

    elif cmd == "groups":
        task_dir = args[0]
        tracker = ProgressTracker(task_dir)
        groups = tracker.get_parallel_groups()
        print(json.dumps({"parallel_groups": groups}, ensure_ascii=False, indent=2))

    elif cmd == "init":
        task_dir = args[0]
        tasks_json = " ".join(args[1:])
        tasks = json.loads(tasks_json)
        tracker = ProgressTracker(task_dir)
        result = tracker.init_dag(tasks)
        print(json.dumps({"status": "initialized", "task_count": len(tasks)}, ensure_ascii=False))

    elif cmd == "report":
        task_dir = args[0]
        tracker = ProgressTracker(task_dir)
        print(tracker.report_progress())

    elif cmd == "visualize":
        task_dir = args[0]
        tracker = ProgressTracker(task_dir)
        print(tracker.export_dag_visualization())

    else:
        print(f"[ERROR] 未知命令: {cmd} | 可用: status, executable, update, groups, init, report, visualize")