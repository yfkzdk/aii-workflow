#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文助手 - 工作流控制界面
直接操控工作流：创建任务、查看状态、验证步骤、恢复中断、清理数据
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 强制UTF-8编码 + 行缓冲，解决Windows终端中文一段一段显示的问题
os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

# 项目根目录
BASE_DIR = Path(__file__).parent.resolve()
WORKFLOWS_DIR = BASE_DIR / "workflows"

# 导入已有模块
sys.path.insert(0, str(BASE_DIR / "scripts"))
try:
    from state_machine import init_state, update_state, safe_transition
    from validator import validate_step
    HAS_CORE_MODULES = True
except ImportError:
    HAS_CORE_MODULES = False

PIPELINE_STEPS = ["planning", "prompt_optimizing", "executing", "verifying", "archiving"]

AGENT_MAP = {
    "planning": "planner",
    "prompt_optimizing": "prompt_optimizer",
    "executing": "coder",
    "verifying": "verifier",
    "archiving": "archivist",
}

STEP_NAMES = {
    "planning": "需求分析",
    "prompt_optimizing": "提示词优化",
    "executing": "代码生成",
    "verifying": "验证测试",
    "archiving": "归档存储",
    "completed": "已完成",
}


def _read_state(task_dir):
    state_file = Path(task_dir) / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return None


def _scan_workflows():
    if not WORKFLOWS_DIR.exists():
        return []
    results = []
    for d in sorted(WORKFLOWS_DIR.iterdir()):
        if d.is_dir() and (d / "state.json").exists():
            state = _read_state(d)
            if state:
                results.append((d, state))
    return results


def _pick_workflow(workflows, prompt="请输入编号"):
    if not workflows:
        print("  没有工作流")
        return None, None
    for i, (d, s) in enumerate(workflows, 1):
        status = s.get("status", "?")
        step = s.get("current_step_index", 0)
        total = len(s.get("pipeline", []))
        retry = s.get("retry_count", 0)
        flag = " [卡住]" if retry >= 3 else ""
        print(f"  {i}. {d.name}  {STEP_NAMES.get(status, status)} ({step}/{total})  重试:{retry}{flag}")
    try:
        choice = input(f"\n{prompt} (0=取消): ").strip()
        idx = int(choice)
        if 1 <= idx <= len(workflows):
            return workflows[idx - 1]
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return None, None


# ─── 功能1: 启动新任务 ───
def create_task():
    print("\n" + "=" * 50)
    print("  启动新任务")
    print("=" * 50)
    print()

    try:
        print("请输入任务描述 (多行直接写，输入空行结束):")
        print("-" * 40)
        lines = []
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        desc = "\n".join(lines).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  已取消")
        return
    if not desc:
        print("  描述不能为空")
        return

    task_id = "TASK-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    task_dir = WORKFLOWS_DIR / task_id

    # 通过 state_machine 创建状态文件
    if HAS_CORE_MODULES:
        init_state(str(task_dir), task_id)
    else:
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "artifacts").mkdir(exist_ok=True)
        state = {
            "task_id": task_id,
            "status": "planning",
            "pipeline": PIPELINE_STEPS,
            "current_step_index": 0,
            "retry_count": 0,
            "max_retries": 3,
            "next_agent": "planner",
            "checkpoint": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        (task_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写入任务描述
    (task_dir / "input.md").write_text(f"# 任务描述\n\n{desc}\n", encoding="utf-8")

    print(f"\n  工作流已创建: {task_id}")
    print(f"  目录: {task_dir}")
    print()
    print("  请将以下指令复制到 Claude Code 执行:")
    print("-" * 50)
    print(f"""读取工作流状态: {task_dir / "state.json"}
读取任务描述: {task_dir / "input.md"}
按照 {PIPELINE_STEPS[0]} 步骤执行工作流。
每步完成后调用: python scripts/state_machine.py update "{task_dir}" <当前步骤> <下一步骤> <下一agent>""")
    print("-" * 50)


# ─── 功能2: 查看工作流状态 ───
def show_status():
    print("\n" + "=" * 50)
    print("  工作流状态总览")
    print("=" * 50)

    workflows = _scan_workflows()
    if not workflows:
        print("\n  没有任何工作流记录")
        return

    print(f"\n  共 {len(workflows)} 个工作流:\n")
    for d, s in workflows:
        status = s.get("status", "?")
        step = s.get("current_step_index", 0)
        total = len(s.get("pipeline", []))
        retry = s.get("retry_count", 0)
        created = s.get("created_at", "")[:19].replace("T", " ")

        tag = STEP_NAMES.get(status, status)
        flag = ""
        if status == "completed":
            flag = " [完成]"
        elif retry >= 3:
            flag = " [卡住-已达最大重试]"

        print(f"  {d.name}")
        print(f"    状态: {tag}  步骤: {step}/{total}  重试: {retry}{flag}")
        print(f"    创建: {created}")
        print()


# ─── 功能3: 查看任务详情 ───
def show_detail():
    print("\n" + "=" * 50)
    print("  任务详情")
    print("=" * 50)

    workflows = _scan_workflows()
    task_dir, state = _pick_workflow(workflows, "选择要查看的工作流")
    if not task_dir or not state:
        return

    print(f"\n  任务ID: {state.get('task_id')}")
    print(f"  状态:   {STEP_NAMES.get(state['status'], state['status'])}")
    print(f"  步骤:   {state.get('current_step_index', 0)}/{len(state.get('pipeline', []))}")
    print(f"  重试:   {state.get('retry_count', 0)}/{state.get('max_retries', 3)}")
    print(f"  下一步: {state.get('next_agent', '无')}")
    created = state.get("created_at", "")[:19].replace("T", " ")
    updated = state.get("updated_at", "")[:19].replace("T", " ")
    print(f"  创建:   {created}")
    print(f"  更新:   {updated}")

    # 任务描述
    input_file = task_dir / "input.md"
    if input_file.exists():
        print(f"\n  任务描述:")
        for line in input_file.read_text(encoding="utf-8").strip().splitlines()[:6]:
            print(f"    {line}")

    # 产出文件
    artifacts = task_dir / "artifacts"
    if artifacts.exists():
        files = list(artifacts.rglob("*"))
        files = [f for f in files if f.is_file()]
        if files:
            print(f"\n  产出文件 ({len(files)} 个):")
            for f in files:
                rel = f.relative_to(artifacts)
                print(f"    {rel}")

    # 最终结果
    final = state.get("final_result")
    if final:
        print(f"\n  最终结果: {final.get('status')} / {final.get('quality_rating')}")
        summary = final.get("summary", "")
        if summary:
            print(f"  摘要: {summary[:100]}")


# ─── 功能4: 验证当前步骤 ───
def validate_current():
    print("\n" + "=" * 50)
    print("  验证当前步骤")
    print("=" * 50)

    if not HAS_CORE_MODULES:
        print("\n  validator.py 不可用，无法验证")
        return

    workflows = _scan_workflows()
    in_progress = [(d, s) for d, s in workflows if s.get("status") != "completed"]
    if not in_progress:
        print("\n  没有进行中的工作流")
        return

    task_dir, state = _pick_workflow(in_progress, "选择要验证的工作流")
    if not task_dir or not state:
        return

    status = state.get("status")
    if status not in PIPELINE_STEPS:
        print(f"\n  当前状态 '{status}' 不是可验证的步骤")
        return

    passed, msg = validate_step(Path(str(task_dir)), status)
    if passed:
        print(f"\n  验证通过  [{status}]")
    else:
        print(f"\n  验证失败  [{status}]")
        print(f"  原因: {msg}")


# ─── 功能5: 恢复中断任务 ───
def recover_task():
    print("\n" + "=" * 50)
    print("  恢复中断任务")
    print("=" * 50)

    workflows = _scan_workflows()
    stuck = [(d, s) for d, s in workflows if s.get("status") != "completed"]
    if not stuck:
        print("\n  没有中断的任务，一切正常")
        return

    task_dir, state = _pick_workflow(stuck, "选择要恢复的工作流")
    if not task_dir or not state:
        return

    task_id = state.get("task_id")
    status = state.get("status")
    next_agent = state.get("next_agent")
    retry = state.get("retry_count", 0)

    if retry >= 3:
        print(f"\n  该任务已达最大重试次数 ({retry}/3)")
        print("  建议: 删除此工作流，重新创建同类任务")

    print(f"\n  请将以下恢复指令复制到 Claude Code 执行:")
    print("-" * 50)
    print(f"""恢复工作流 - 从断点继续

任务ID: {task_id}
当前状态: {status}
下一步Agent: {next_agent or '无'}

指令:
1. 读取状态文件: {task_dir / "state.json"}
2. 读取任务描述: {task_dir / "input.md"}
3. 从 {status} 步骤继续执行工作流
4. 完成后调用: python scripts/state_machine.py update "{task_dir}" {status} <下一步骤> <下一agent>""")
    print("-" * 50)


# ─── 功能6: 清理已完成工作流 ───
def cleanup_workflows():
    print("\n" + "=" * 50)
    print("  清理已完成工作流")
    print("=" * 50)

    workflows = _scan_workflows()
    done = [(d, s) for d, s in workflows if s.get("status") == "completed"]
    if not done:
        print("\n  没有已完成的工作流需要清理")
        return

    print(f"\n  找到 {len(done)} 个已完成的工作流:\n")
    for i, (d, s) in enumerate(done, 1):
        print(f"  {i}. {d.name}")

    try:
        choice = input(f"\n确认删除以上 {len(done)} 个工作流? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("  已取消")
        return

    if choice == "y":
        for d, _ in done:
            shutil.rmtree(d, ignore_errors=True)
            print(f"  已删除: {d.name}")
        print(f"\n  清理完成，共删除 {len(done)} 个工作流")
    else:
        print("  已取消")


# ─── 主菜单 ───
def main():
    print("\n" + "=" * 50)
    print("       上下文助手 - 工作流控制界面")
    print("=" * 50)

    if not HAS_CORE_MODULES:
        print("\n  [!] state_machine / validator 模块未找到")
        print("  [!] 部分功能将使用内置逻辑")

    if not WORKFLOWS_DIR.exists():
        WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        print("\n" + "-" * 50)
        print("  1. 启动新任务")
        print("  2. 查看工作流状态")
        print("  3. 查看任务详情")
        print("  4. 验证当前步骤")
        print("  5. 恢复中断任务")
        print("  6. 清理已完成工作流")
        print("  0. 退出")
        print("-" * 50)

        try:
            choice = input("\n请输入选项 (0-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n退出")
            break

        if choice == "1":
            create_task()
        elif choice == "2":
            show_status()
        elif choice == "3":
            show_detail()
        elif choice == "4":
            validate_current()
        elif choice == "5":
            recover_task()
        elif choice == "6":
            cleanup_workflows()
        elif choice == "0":
            print("\n再见")
            break
        else:
            print("  无效选项")


if __name__ == "__main__":
    main()