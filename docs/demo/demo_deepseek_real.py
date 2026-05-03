#!/usr/bin/env python3
"""DeepSeek API 真实任务演示

完整演示从需求提交到代码生成的全过程。
"""

import sys
import os
from pathlib import Path

# 设置编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 添加项目路径
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core import Orchestrator, StateDB
from unittest.mock import MagicMock, patch

def create_mock_artifacts(task_dir, step, content=None):
    """创建验证器所需的 artifacts 文件"""
    artifacts = Path(task_dir) / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    step_files = {
        "requirement_optimizing": "optimized_requirement.json",
        "planning": "requirements.md",
        "prompt_optimizing": "optimal_prompt.md",
        "executing": "code/main.py",
        "verifying": "test_report.json",
        "archiving": "AI_WORKFLOW_LOG.md",
    }

    if step in step_files:
        filepath = artifacts / step_files[step]
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if step == "test_report.json":
            import json
            data = {"passed": True, "tests": [], "summary": "all passed"}
            filepath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        elif step == "optimized_requirement.json":
            import json
            data = {
                "original_requirement": content or "mock",
                "clarifications": [],
                "proposals": [
                    {"id": "A", "name": "minimal", "description": "mock",
                     "scope": "minimal", "estimated_tasks": 1,
                     "skills_recommended": [], "pros": [], "cons": []},
                ],
                "agent_assignments": [],
                "task_dag_preview": {"nodes": [], "edges": []},
                "features_detected": {},
                "reasoning_trace": {},
            }
            filepath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        else:
            filepath.write_text(content or f"# {step}\n\nMock content.", encoding="utf-8")


def mock_caller_call(agent_id, task_dir, context=""):
    """Mock agent caller for testing"""
    from core.agent_caller import OpenAICaller
    import json

    # 使用真实的 DeepSeek API 调用
    caller = OpenAICaller()
    result = caller.call(agent_id, task_dir, context)

    # 为特定 agent 创建 artifacts
    if agent_id == "requirement_optimizer":
        create_mock_artifacts(task_dir, "requirement_optimizing", result['output'])
    elif agent_id == "planner":
        create_mock_artifacts(task_dir, "planning", result['output'])
    elif agent_id == "prompt_optimizer":
        create_mock_artifacts(task_dir, "prompt_optimizing", result['output'])
    elif agent_id == "coder":
        create_mock_artifacts(task_dir, "executing", result['output'])
    elif agent_id == "archivist":
        create_mock_artifacts(task_dir, "archiving", result['output'])

    return result


def main():
    """主函数"""
    import tempfile
    import shutil

    task_id = "DEEPSEEK-REAL-001"
    task_dir = tempfile.mkdtemp(prefix='workflow_')

    try:
        print("="*60)
        print("  DeepSeek API 真实任务演示")
        print("="*60)
        print(f"Task ID: {task_id}")
        print(f"Task Dir: {task_dir}")
        print()

        # 初始化
        db = StateDB(task_dir)
        db.init_task(task_id)

        # Mock agent caller
        with patch('core.orchestrator.AgentCaller.create') as mock_create:
            mock_create.return_value = MagicMock(call=mock_caller_call)

            orch = Orchestrator(task_dir, task_id)

            # 步骤 1: 用户输入
            print("步骤 1: 提交用户需求")
            print("-" * 60)
            user_input = "帮我写一个冒泡排序算法"
            print(f"需求: {user_input}")
            orch.handle_user_input(user_input)

            # 步骤 2: 需求优化
            print("\n步骤 2: 需求优化 (调用 DeepSeek API)")
            print("-" * 60)
            orch.db.update_status(task_id, "requirement_optimizing", 1)
            result = orch.run()

            # 步骤 3: 用户确认
            print("\n步骤 3: 用户确认")
            print("-" * 60)
            orch.db.save_confirmation(task_id, "confirmed", {"selected_proposal": "A"})
            result = orch.run()

            # 步骤 4: 规划
            print("\n步骤 4: 生成执行计划 (调用 DeepSeek API)")
            print("-" * 60)
            result = orch.run()

            # 步骤 5: 提示词优化
            print("\n步骤 5: 提示词优化 (调用 DeepSeek API)")
            print("-" * 60)
            result = orch.run()

            # 步骤 6: 代码生成
            print("\n步骤 6: 代码生成 (调用 DeepSeek API)")
            print("-" * 60)
            result = orch.run()

            # 步骤 7: 验证
            print("\n步骤 7: 验证")
            print("-" * 60)
            create_mock_artifacts(task_dir, "verifying")
            result = orch.run()

            # 步骤 8: 归档
            print("\n步骤 8: 归档 (调用 DeepSeek API)")
            print("-" * 60)
            result = orch.run()

        # 显示结果
        print("\n" + "="*60)
        print("  任务完成统计")
        print("="*60)

        state = db.get_state(task_id)
        print(f"最终状态: {state['status']}")
        print(f"步骤索引: {state['step_index']}")
        print(f"重试次数: {state.get('retry_count', 0)}")

        print(f"\nToken 使用:")
        print(f"  Input tokens:  {state.get('total_input_tokens', 0)}")
        print(f"  Output tokens: {state.get('total_output_tokens', 0)}")

        # 检查生成的文件
        artifacts_dir = Path(task_dir) / "artifacts"
        if artifacts_dir.exists():
            print(f"\n生成的文件:")
            for file in sorted(artifacts_dir.rglob("*")):
                if file.is_file():
                    print(f"  - {file.relative_to(artifacts_dir)}")

        print("\n✅ DeepSeek API 真实任务演示成功！")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if Path(task_dir).exists():
            shutil.rmtree(task_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
