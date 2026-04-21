"""DAG调度器 — 读取任务DAG并生成调度计划

此模块提供：
- read_dag: 读取 state.json 中的 task_dag
- generate_schedule: 输出调度计划 JSON
- mark_phase_started/completed: 更新进度

注意：此模块不执行任何 Agent，不做任何 asyncio/并发。
真正的并发执行由 Claude Code Agent 工具的并行能力完成。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils import atomic_write_json


class DAGRunner:
    """DAG调度器：生成调度计划，不执行Agent"""

    def __init__(self, task_dir: str):
        self.task_dir = Path(task_dir)
        self.state_file = self.task_dir / "state.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载 state.json"""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        """保存 state.json"""
        self.state["updated_at"] = datetime.now().isoformat()
        atomic_write_json(self.state_file, self.state)

    def read_dag(self) -> Dict[str, Any]:
        """读取 state.json 中的 task_dag，无则返回空 dict"""
        return self.state.get("task_dag", {})

    def generate_schedule(self) -> Dict[str, Any]:
        """从 task_dag 依赖图生成阶段调度计划"""
        dag = self.read_dag()
        tasks = dag.get("tasks", [])
        if not tasks:
            return {"phases": [], "total_phases": 0, "parallel_opportunities": []}

        completed_ids = set()
        phases = []
        remaining = list(tasks)

        while remaining:
            phase_tasks = []
            for t in remaining:
                deps = t.get("dependencies", [])
                if all(d in completed_ids for d in deps):
                    phase_tasks.append(t)

            if not phase_tasks:
                # 检测到循环依赖，将剩余任务放入最终阶段
                phase_tasks = remaining

            phase_entry = {
                "phase": len(phases),
                "serial": len(phase_tasks) == 1,
                "agents": [t["id"] for t in phase_tasks]
            }
            phases.append(phase_entry)
            completed_ids.update(t["id"] for t in phase_tasks)
            remaining = [t for t in remaining if t["id"] not in completed_ids]

        parallel_opps = [
            {"phase": p["phase"], "agents": p["agents"]}
            for p in phases if not p["serial"]
        ]

        return {
            "phases": phases,
            "total_phases": len(phases),
            "parallel_opportunities": parallel_opps
        }

    def mark_phase_started(self, phase_index: int) -> Dict[str, Any]:
        """标记阶段开始"""
        schedule = self.generate_schedule()
        if phase_index < 0 or phase_index >= len(schedule["phases"]):
            return {"error": f"Invalid phase_index {phase_index}"}

        phase = schedule["phases"][phase_index]
        tasks = self.state.get("task_dag", {}).get("tasks", [])

        for task in tasks:
            if task["id"] in phase["agents"] and task.get("status") == "pending":
                task["status"] = "in_progress"
                task["started_at"] = datetime.now().isoformat()

        self._save_state()
        return {"status": "started", "phase": phase_index, "agents": phase["agents"]}

    def mark_phase_completed(self, phase_index: int) -> Dict[str, Any]:
        """标记阶段完成"""
        schedule = self.generate_schedule()
        if phase_index < 0 or phase_index >= len(schedule["phases"]):
            return {"error": f"Invalid phase_index {phase_index}"}

        phase = schedule["phases"][phase_index]
        tasks = self.state.get("task_dag", {}).get("tasks", [])

        for task in tasks:
            if task["id"] in phase["agents"] and task.get("status") == "in_progress":
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()

        self._save_state()
        return {"status": "completed", "phase": phase_index, "agents": phase["agents"]}

    def get_executable_now(self) -> Dict[str, Any]:
        """获取当前可执行的任务（依赖全部完成的 pending 任务）"""
        dag = self.read_dag()
        tasks = dag.get("tasks", [])
        completed_ids = {t["id"] for t in tasks if t.get("status") == "completed"}

        executable = [
            {
                "id": t["id"],
                "name": t.get("name", t["id"]),
                "dependencies": t.get("dependencies", [])
            }
            for t in tasks
            if t.get("status") == "pending"
            and all(d in completed_ids for d in t.get("dependencies", []))
        ]

        return {"executable_tasks": executable}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  read_dag <task_dir>           - Read task_dag from state.json")
        print("  generate_schedule <task_dir>  - Generate execution schedule")
        print("  mark_started <task_dir> <phase_index>  - Mark phase as started")
        print("  mark_completed <task_dir> <phase_index> - Mark phase as completed")
        print("  executable <task_dir>        - Get currently executable tasks")
        sys.exit(0)

    cmd, *args = sys.argv[1:]

    if cmd == "read_dag":
        # read_dag <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python dag_runner.py read_dag <task_dir>")
            sys.exit(1)

        runner = DAGRunner(args[0])
        dag = runner.read_dag()
        print(json.dumps(dag, ensure_ascii=False, indent=2))

    elif cmd == "generate_schedule":
        # generate_schedule <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python dag_runner.py generate_schedule <task_dir>")
            sys.exit(1)

        runner = DAGRunner(args[0])
        schedule = runner.generate_schedule()
        print(json.dumps(schedule, ensure_ascii=False, indent=2))

    elif cmd == "mark_started":
        # mark_started <task_dir> <phase_index>
        if len(args) < 2:
            print("[ERROR] Usage: python dag_runner.py mark_started <task_dir> <phase_index>")
            sys.exit(1)

        runner = DAGRunner(args[0])
        result = runner.mark_phase_started(int(args[1]))
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "mark_completed":
        # mark_completed <task_dir> <phase_index>
        if len(args) < 2:
            print("[ERROR] Usage: python dag_runner.py mark_completed <task_dir> <phase_index>")
            sys.exit(1)

        runner = DAGRunner(args[0])
        result = runner.mark_phase_completed(int(args[1]))
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "executable":
        # executable <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python dag_runner.py executable <task_dir>")
            sys.exit(1)

        runner = DAGRunner(args[0])
        result = runner.get_executable_now()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print("[ERROR] Unknown command:", cmd)
        print("Available commands:")
        print("  read_dag <task_dir>           - Read task_dag from state.json")
        print("  generate_schedule <task_dir>  - Generate execution schedule")
        print("  mark_started <task_dir> <phase_index>  - Mark phase as started")
        print("  mark_completed <task_dir> <phase_index> - Mark phase as completed")
        print("  executable <task_dir>        - Get currently executable tasks")
        sys.exit(1)