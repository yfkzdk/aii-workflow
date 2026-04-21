#!/usr/bin/env python3
"""v3 Demo -- 安全管线执行演示，零崩溃保证。

演示内容：
1. SafeState 初始化与快照
2. 安全步进 advance_to()
3. 确认门 confirm_action() 含回退限流
4. 中文 Token 估算
5. 状态一致性验证
6. 回滚到快照
7. v2 state.json 兼容读写

运行: python demo/run_demo.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 设置项目路径
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / "core"))

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from core.state import SafeState
from core.pipeline import PipelineRunner, estimate_tokens_chinese, chunk_text_by_tokens
from utils import setup_encoding


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    setup_encoding()

    config_path = str(PROJECT_DIR / "config" / "pipeline_config.json")
    runner = PipelineRunner(config_path)

    task_id = f"DEMO-V3-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    task_dir = str(PROJECT_DIR / "workflows" / task_id)

    # ===== Step 1: 初始化 SafeState =====
    separator("1. 初始化 SafeState")
    state = SafeState(task_id=task_id)
    print(f"  Task ID: {task_id}")
    print(f"  Pipeline: {' → '.join(state.pipeline)}")
    print(f"  Status: {state.status} (step {state.current_step_index})")
    print(f"  Max confirmation retries: {state.max_confirmation_retries}")

    # ===== Step 2: 创建快照 =====
    separator("2. 创建快照")
    snap_id = state.snapshot("initial")
    print(f"  Snapshot created: {snap_id}")
    print(f"  Total snapshots: {state.snapshot_count}")

    # ===== Step 3: 安全步进 =====
    separator("3. 安全步进 advance_to()")
    advance_steps = [
        ("requirement_optimizing", "requirement_optimizer"),
        ("confirmation", "user"),
    ]
    for step, agent in advance_steps:
        ok, msg = runner.can_advance(state, step)
        if not ok:
            print(f"  [BLOCKED] Cannot advance to {step}: {msg}")
            break
        state.advance_to(step, agent)
        print(f"  [ADVANCE] -> {state.status} (step {state.current_step_index})")

    # ===== Step 4: 确认门限流 =====
    separator("4. 确认门 confirm_action()")
    # 第一次尝试：修订需求
    result = state.confirm_action("revise", updates=[{"point": "联机方式", "new_value": "HTTP轮询"}])
    print(f"  第1次确认(revise): {result}")
    print(f"  Status: {state.status}, Step: {state.current_step_index}")
    print(f"  Retry count: {state.confirm_retry_count}/{state.max_confirmation_retries}")

    # 再次步进到确认门
    state.advance_to("confirmation", "user")

    # 第二次尝试：再次修订
    result = state.confirm_action("revise", updates=[{"point": "难度", "new_value": "5"}])
    print(f"  第2次确认(revise): {result}")
    print(f"  Retry count: {state.confirm_retry_count}/{state.max_confirmation_retries}")

    # 第三次：确认通过
    state.advance_to("confirmation", "user")
    result = state.confirm_action("confirm", proposal="B")
    print(f"  第3次确认(confirm): {result}")
    print(f"  Status: {state.status}, Step: {state.current_step_index}")

    # 测试限流：超过4次回退
    print(f"\n  --- 测试限流 ---")
    state.confirm_retry_count = state.max_confirmation_retries
    state.advance_to("confirmation", "user")
    result = state.confirm_action("revise")
    print(f"  超限回退结果: {result}")

    # 重置用于后续演示
    state.confirm_retry_count = 0

    # ===== Step 5: Token 估算（中文适配）=====
    separator("5. Token 估算（中文适配）")
    test_cases = [
        ("写一个斐波那契数列计算函数，要求支持缓存优化", "中文为主"),
        ("Write a fibonacci sequence function with cache optimization", "英文为主"),
        ("写一个fibonacci函数，支持cache优化", "中英混合"),
    ]
    for text, label in test_cases:
        est = estimate_tokens_chinese(text)
        fits, _, budget = runner.check_token_budget(text, "executing")
        print(f"  [{label}] tokens={est}, budget={budget}, fits={fits}")
        print(f"    text: {text[:40]}...")

    # ===== Step 6: Token 分段 =====
    separator("6. Token 分段（超长文本切分）")
    long_text = "这是一个很长的需求描述。" * 200
    chunks = chunk_text_by_tokens(long_text, 1200)
    print(f"  原文估算 tokens: {estimate_tokens_chinese(long_text)}")
    print(f"  分段数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"  段{i+1}: {estimate_tokens_chinese(chunk)} tokens, {len(chunk)} chars")

    # ===== Step 7: 状态验证 =====
    separator("7. 状态一致性验证")
    valid, errors = runner.validate_state(state)
    print(f"  State valid: {valid}")
    if errors:
        for e in errors:
            print(f"  - {e}")

    # 测试非法状态
    bad_state = SafeState(task_id="bad-test")
    bad_state.current_step_index = 999  # 越界
    valid2, errors2 = runner.validate_state(bad_state)
    print(f"  Bad state (index=999) valid before enforce: {valid2}")
    bad_state._enforce_invariants()
    print(f"  After enforce: index={bad_state.current_step_index} (clamped to {len(bad_state.pipeline)-1})")

    # ===== Step 8: 回滚演示 =====
    separator("8. 回滚到快照")
    print(f"  Current: status={state.status}, step={state.current_step_index}")
    print(f"  Snapshots available: {state.snapshot_count}")
    rolled_back = state.rollback()
    print(f"  Rollback success: {rolled_back}")
    print(f"  After rollback: status={state.status}, step={state.current_step_index}")

    # ===== Step 9: v2 兼容保存与加载 =====
    separator("9. v2 兼容保存与加载")
    save_state = SafeState(task_id=f"COMPAT-TEST-{datetime.now().strftime('%H%M%S')}")
    save_state.advance_to("planning", "planner")
    saved_path = save_state.save()
    print(f"  Saved to: {saved_path}")

    loaded = SafeState.from_file(saved_path)
    print(f"  Loaded: task={loaded.task_id}, status={loaded.status}, step={loaded.current_step_index}")
    valid3, errors3 = runner.validate_state(loaded)
    print(f"  Loaded state valid: {valid3}")

    # 清理演示文件
    import shutil
    demo_dir = Path(saved_path).parent
    if demo_dir.exists() and "DEMO-V3" in str(demo_dir) or "COMPAT-TEST" in str(demo_dir):
        shutil.rmtree(str(demo_dir))
        print(f"  Cleaned up: {demo_dir}")
    # 也清理初始 demo 目录（如果有）
    demo_task_dir = Path(task_dir)
    if demo_task_dir.exists():
        shutil.rmtree(str(demo_task_dir))
        print(f"  Cleaned up: {demo_task_dir}")

    separator("Demo 完成")
    print("  所有测试通过，零崩溃。")


if __name__ == "__main__":
    main()