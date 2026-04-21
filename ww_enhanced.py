#!/usr/bin/env python3
"""上下文助手 - 增强版 CLI 入口

支持 status / version / recover / help 命令和任务创建。
与 ww_simple.py 共享底层逻辑，提供增强版 UI 输出。
"""

import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from utils import scan_workflows, format_status_line, setup_encoding


class Colors:
    @classmethod
    def success(cls, text): return f"\033[32m[SUCCESS]\033[0m {text}"
    @classmethod
    def error(cls, text): return f"\033[31m[ERROR]\033[0m {text}"
    @classmethod
    def info(cls, text): return f"\033[36m[INFO]\033[0m {text}"
    @classmethod
    def title(cls, text): return f"\033[1;33m=== {text} ===\033[0m"


class WorkflowLauncher:
    def __init__(self):
        self.workflow_dir = PROJECT_DIR
        self.config_path = self.workflow_dir / "config" / "user_prefs.json"
        self.config = self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": "2.0"}

    def show_version(self):
        version = self.config.get("version", "2.0")
        print(Colors.title(f"上下文助手 v{version}"))
        print()
        print("增强版功能:")
        print("  - 智能任务分类与输入收集")
        print("  - 需求优化与方案选择")
        print("  - 用户确认门")
        print("  - 并行执行调度")
        print("  - 一键启动与恢复")

    def show_status(self):
        """扫描并显示所有工作流任务状态"""
        workflows_dir = self.workflow_dir / "workflows"
        tasks = scan_workflows(str(workflows_dir))

        if not tasks:
            print(Colors.info("暂无任务"))
            return

        print(Colors.title("任务状态"))
        print(f"{'任务ID':<30} {'状态':<25} {'进度':>5}  {'更新时间'}")
        print("-" * 80)
        for task in tasks:
            print(format_status_line(task))

        completed = sum(1 for t in tasks if t["status"] == "completed")
        running = sum(1 for t in tasks if t["status"] not in ("completed", "cancelled"))
        print(f"\n共 {len(tasks)} 个任务 | {completed} 已完成 | {running} 进行中")

    def show_recover(self):
        """找到最近未完成的任务，输出恢复指令"""
        workflows_dir = self.workflow_dir / "workflows"
        tasks = scan_workflows(str(workflows_dir))

        unfinished = [
            t for t in tasks
            if t["status"] not in ("completed", "cancelled")
        ]

        if not unfinished:
            print(Colors.info("没有未完成的任务"))
            return

        unfinished.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        task = unfinished[0]

        print(Colors.title("恢复任务"))
        print(f"  任务ID: {task['task_id']}")
        print(f"  状态:   {task['status']}")
        print(f"  进度:   {task['step_index']}/{len(task['pipeline'])}")
        print(f"  目录:   {task['dir']}")
        print()
        print("恢复指令:")
        pipeline = task.get("pipeline", [])
        step_idx = task.get("step_index", 0)
        if step_idx < len(pipeline):
            current_step = pipeline[step_idx]
            print(f'  python scripts/state_machine.py update "{task["dir"]}" {current_step} <next_step> <next_agent>')
        print(f'  cd "{task["dir"]}"')

    def show_help(self):
        print(Colors.title("上下文助手 - 帮助"))
        print()
        print("用法:")
        print("  python ww_enhanced.py status              查看所有任务状态")
        print("  python ww_enhanced.py version             显示版本信息")
        print("  python ww_enhanced.py recover             恢复最近未完成任务")
        print("  python ww_enhanced.py help                显示此帮助")
        print('  python ww_enhanced.py "任务描述"          创建新任务')
        print()
        print("任务描述示例:")
        print('  python ww_enhanced.py "写一个斐波那契函数"')

    def run_new_task(self, description: str):
        """创建新任务：初始化状态机和输入收集"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_id = f"TASK-{timestamp}"
        task_dir = str(self.workflow_dir / "workflows" / task_id)

        try:
            from state_machine import init_state
            init_state(task_dir, task_id, enhanced=True)
        except Exception as e:
            print(Colors.error(f"状态机初始化失败: {e}"))
            sys.exit(1)

        # 添加用户输入
        try:
            from input_collector import add_chunk
            add_chunk(task_dir, description)
        except Exception:
            state_file = Path(task_dir) / "state.json"
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            state.setdefault("user_input", {})
            state["user_input"]["chunks"] = state["user_input"].get("chunks", [])
            state["user_input"]["chunks"].append({
                "content": description,
                "timestamp": datetime.now().isoformat()
            })
            from utils import atomic_write_json
            atomic_write_json(state_file, state)

        print(Colors.success(f"任务已创建: {task_id}"))
        print(f"     目录: {task_dir}")
        print(f"     状态: input_collecting")
        print()
        print("下一步:")
        print(f'  1. 继续添加输入: python scripts/input_collector.py add "{task_dir}" "更多描述"')
        print(f'  2. 完成输入:     python scripts/input_collector.py complete "{task_dir}"')
        print(f"  3. 查看状态:     python ww_enhanced.py status")

    def run(self):
        setup_encoding()

        if len(sys.argv) < 2:
            self.show_help()
            return

        cmd = sys.argv[1].lower()

        if cmd == "version":
            self.show_version()
        elif cmd in ("help", "--help", "-h"):
            self.show_help()
        elif cmd == "status":
            self.show_status()
        elif cmd == "recover":
            self.show_recover()
        else:
            description = " ".join(sys.argv[1:])
            self.run_new_task(description)


def main():
    try:
        launcher = WorkflowLauncher()
        launcher.run()
    except Exception as e:
        print(Colors.error(f"执行失败: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()