#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端演示脚本 - 展示完整工作流程

此脚本自动化演示：
1. 初始化任务（state_machine init）
2. 收集输入（input_collector add × N）
3. 标记输入完成（input_collector complete）
4. 状态流转到 requirement_optimizing
5. 生成占位方案（requirement_optimizer placeholder）
6. 用户确认（state_machine confirm）
7. 查看进度（progress_tracker status）
8. 生成 DAG 调度（dag_runner generate_schedule）
9. 输出最终状态
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def run_cmd(desc: str, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """运行命令并打印描述"""
    print(f"\n{'='*60}")
    print(f"[步骤] {desc}")
    print(f"{'='*60}")
    print(f"$ {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=str(PROJECT_DIR)
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[stderr] {result.stderr}")

    if check and result.returncode != 0:
        print(f"[ERROR] 命令失败，退出码: {result.returncode}")
        sys.exit(1)

    return result


def main():
    setup_encoding()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    task_id = f"DEMO-{timestamp}"
    task_dir = str(PROJECT_DIR / "workflows" / task_id)

    print("=" * 60)
    print("       上下文助手 - 端到端演示")
    print("=" * 60)
    print(f"\n任务ID: {task_id}")
    print(f"任务目录: {task_dir}")

    # 步骤 1: 初始化状态机
    run_cmd(
        "1. 初始化任务（state_machine init）",
        [sys.executable, str(SCRIPTS_DIR / "state_machine.py"), "init", task_dir, task_id, "true"]
    )

    # 步骤 2: 收集用户输入
    run_cmd(
        "2a. 添加第一条输入（input_collector add）",
        [sys.executable, str(SCRIPTS_DIR / "input_collector.py"), "add", task_dir, "写一个斐波那契数列计算函数"]
    )

    run_cmd(
        "2b. 添加第二条输入",
        [sys.executable, str(SCRIPTS_DIR / "input_collector.py"), "add", task_dir, "要求支持缓存优化，避免重复计算"]
    )

    run_cmd(
        "2c. 添加第三条输入",
        [sys.executable, str(SCRIPTS_DIR / "input_collector.py"), "add", task_dir, "输出结果保存到文件 /done"]
    )

    # 步骤 3: 标记输入完成
    run_cmd(
        "3. 标记输入完成（input_collector complete）",
        [sys.executable, str(SCRIPTS_DIR / "input_collector.py"), "complete", task_dir]
    )

    # 步骤 4: 状态流转到 requirement_optimizing
    run_cmd(
        "4. 状态流转到 requirement_optimizing",
        [sys.executable, str(SCRIPTS_DIR / "state_machine.py"), "update", task_dir, "input_collecting", "requirement_optimizing", "requirement_optimizer"]
    )

    # 步骤 5: 生成占位方案（创建模拟的优化结果）
    print("\n" + "="*60)
    print("[步骤] 5. 生成占位方案（requirement_optimizer placeholder）")
    print("="*60)

    artifacts_dir = Path(task_dir) / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    placeholder_result = {
        "original_requirement": "写一个斐波那契数列计算函数，要求支持缓存优化",
        "clarifications": [
            {
                "point": "输出格式",
                "original": "保存到文件",
                "inferred": "返回结果同时写入文件",
                "confidence": 0.85,
                "needs_user_confirm": False
            }
        ],
        "proposals": [
            {
                "id": "A",
                "name": "最小可行方案",
                "description": "基础递归实现",
                "scope": "核心功能",
                "estimated_tasks": 3,
                "pros": ["实现简单", "快速"],
                "cons": ["性能一般"]
            },
            {
                "id": "B",
                "name": "标准方案",
                "description": "带缓存的斐波那契函数",
                "scope": "核心 + 缓存优化",
                "estimated_tasks": 5,
                "pros": ["性能好", "可扩展"],
                "cons": ["稍复杂"]
            },
            {
                "id": "C",
                "name": "完整方案",
                "description": "包含测试和文档",
                "scope": "全功能实现",
                "estimated_tasks": 8,
                "pros": ["完整", "可维护"],
                "cons": ["开发时间长"]
            }
        ],
        "agent_assignments": [
            {"agent_id": "coder", "role": "核心实现", "skills": [{"id": "python", "source": "auto_match"}]}
        ],
        "task_dag_preview": {
            "nodes": ["fib_impl", "cache_module", "file_output"],
            "edges": [["fib_impl", "cache_module"], ["cache_module", "file_output"]],
            "parallel_groups": []
        },
        "features_detected": {
            "has_backend": {"detected": False},
            "has_frontend": {"detected": False},
            "complexity_score": 2.5,
            "domain_tags": ["python", "algorithm"]
        }
    }

    with open(artifacts_dir / "optimized_requirement.json", "w", encoding="utf-8") as f:
        json.dump(placeholder_result, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已生成占位优化结果: {artifacts_dir / 'optimized_requirement.json'}")

    # 步骤 6: 用户确认
    run_cmd(
        "6a. 状态流转到 confirmation",
        [sys.executable, str(SCRIPTS_DIR / "state_machine.py"), "update", task_dir, "requirement_optimizing", "confirmation", "user"]
    )

    run_cmd(
        "6b. 用户确认方案 B",
        [sys.executable, str(SCRIPTS_DIR / "state_machine.py"), "confirm", task_dir, "confirm", "B"]
    )

    # 步骤 7: 查看进度
    # 注意：由于任务 DAG 尚未在 planning 阶段创建，此步骤可能失败
    # 但这是正常的流程行为
    print("\n" + "="*60)
    print("[步骤] 7. 查看进度（progress_tracker status）")
    print("="*60)
    print("[INFO] 任务 DAG 尚未创建（需等待 planning 阶段）")
    print("[INFO] 跳过此步骤...")

    # 步骤 8: 生成 DAG 调度
    # 注意：需要 planning 阶段先创建 task_dag
    print("\n" + "="*60)
    print("[步骤] 8. 生成 DAG 调度（dag_runner generate_schedule）")
    print("="*60)
    print("[INFO] 需要先完成 planning 阶段")
    print("[INFO] 跳过此步骤...")

    # 步骤 9: 输出最终状态
    print("\n" + "="*60)
    print("[步骤] 9. 输出最终状态")
    print("="*60)

    state_file = Path(task_dir) / "state.json"
    with open(state_file, "r", encoding="utf-8") as f:
        final_state = json.load(f)

    print(f"任务ID: {final_state.get('task_id')}")
    print(f"状态:   {final_state.get('status')}")
    print(f"进度:   {final_state.get('current_step_index')}/{len(final_state.get('pipeline', []))}")
    print(f"管线:   {' → '.join(final_state.get('pipeline', []))}")
    print(f"创建时间: {final_state.get('created_at')}")
    print(f"更新时间: {final_state.get('updated_at')}")

    print("\n" + "="*60)
    print("       演示完成！")
    print("="*60)
    print(f"\n任务目录: {task_dir}")
    print("您可以继续手动操作：")
    print(f"  python ww_simple.py status")
    print(f"  python ww_simple.py recover")


def setup_encoding():
    """设置UTF-8编码环境"""
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


if __name__ == "__main__":
    main()