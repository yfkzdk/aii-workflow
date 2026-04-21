#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上下文助手 - 核心 CLI 入口

用法:
  python ww_simple.py status              查看所有任务状态
  python ww_simple.py version             显示版本信息
  python ww_simple.py recover             恢复最近未完成任务
  python ww_simple.py help                显示帮助
  python ww_simple.py "任务描述"          创建新任务
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 设置项目根目录
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

from utils import scan_workflows, format_status_line, setup_encoding


def cmd_status():
    """扫描 workflows/ 下所有任务，格式化输出状态列表"""
    workflows_dir = PROJECT_DIR / "workflows"
    tasks = scan_workflows(str(workflows_dir))

    if not tasks:
        print("[INFO] 暂无任务")
        return

    print(f"{'任务ID':<30} {'状态':<25} {'进度':>5}  {'更新时间'}")
    print("-" * 80)
    for task in tasks:
        print(format_status_line(task))

    # 统计
    completed = sum(1 for t in tasks if t["status"] == "completed")
    running = sum(1 for t in tasks if t["status"] not in ("completed", "cancelled"))
    print(f"\n共 {len(tasks)} 个任务 | {completed} 已完成 | {running} 进行中")


def cmd_version():
    """读取 config/user_prefs.json 显示版本"""
    config_path = PROJECT_DIR / "config" / "user_prefs.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        version = config.get("version", "unknown")
        print(f"上下文助手 v{version}")
    except (FileNotFoundError, json.JSONDecodeError):
        print("上下文助手 v2.0")


def cmd_recover():
    """找到最近一个未完成任务，输出恢复指令"""
    workflows_dir = PROJECT_DIR / "workflows"
    tasks = scan_workflows(str(workflows_dir))

    # 过滤未完成任务
    unfinished = [
        t for t in tasks
        if t["status"] not in ("completed", "cancelled")
    ]

    if not unfinished:
        print("[INFO] 没有未完成的任务")
        return

    # 按更新时间排序，取最近
    unfinished.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    task = unfinished[0]

    print(f"[RECOVER] 最近未完成任务:")
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


def cmd_help():
    """显示帮助信息"""
    print("=" * 60)
    print("       上下文助手 (AII Workflow) - 命令行工具")
    print("=" * 60)
    print()
    print("用法:")
    print("  python ww_simple.py status              查看所有任务状态")
    print("  python ww_simple.py version             显示版本信息")
    print("  python ww_simple.py recover             恢复最近未完成任务")
    print("  python ww_simple.py help                显示此帮助")
    print('  python ww_simple.py "任务描述"          创建新任务')
    print()
    print("任务描述示例:")
    print('  python ww_simple.py "写一个斐波那契函数"')
    print('  python ww_simple.py "分析项目结构"')
    print()
    print("管线阶段:")
    print("  input_collecting → requirement_optimizing → confirmation")
    print("  → planning → prompt_optimizing → executing → verifying → archiving")


def cmd_new_task(description: str):
    """创建新任务：初始化状态机和输入收集"""
    # 生成任务ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_id = f"TASK-{timestamp}"
    task_dir = str(PROJECT_DIR / "workflows" / task_id)

    # 初始化状态机
    try:
        from state_machine import init_state
        init_state(task_dir, task_id, enhanced=True)
    except Exception as e:
        print(f"[ERROR] 状态机初始化失败: {e}")
        sys.exit(1)

    # 添加用户输入
    try:
        from input_collector import add_input
        add_input(task_dir, description)
    except Exception:
        # 如果 input_collector 不可用，直接写入
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

    print(f"[OK] 任务已创建: {task_id}")
    print(f"     目录: {task_dir}")
    print(f"     状态: input_collecting")
    print()
    print("下一步:")
    print("  1. 继续添加输入: python scripts/input_collector.py add " + f'"{task_dir}" "更多描述"')
    print("  2. 完成输入:     python scripts/input_collector.py complete " + f'"{task_dir}"')
    print("  3. 查看状态:     python ww_simple.py status")


def main():
    setup_encoding()

    if len(sys.argv) < 2:
        cmd_help()
        return

    arg = sys.argv[1]

    if arg.lower() in ("status", "-s", "--status"):
        cmd_status()
    elif arg.lower() in ("version", "-v", "--version"):
        cmd_version()
    elif arg.lower() in ("recover", "-r", "--recover"):
        cmd_recover()
    elif arg.lower() in ("help", "-h", "--help"):
        cmd_help()
    else:
        # 任务描述 — 合并所有参数
        description = " ".join(sys.argv[1:])
        cmd_new_task(description)


if __name__ == "__main__":
    main()