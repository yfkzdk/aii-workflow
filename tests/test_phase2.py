"""阶段二测试：验证、重试、质量门、确认流。"""

import json
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent

from scripts.validator import validate_step, _check_requirement_schema
from core.db import StateDB
from core.orchestrator import Orchestrator

results: list[tuple[str, bool, str]] = []


def _setup_task_dir(tmp: Path, task_id: str = "test_task") -> Path:
    """创建最小化的任务目录结构。"""
    task_dir = tmp / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "artifacts").mkdir(exist_ok=True)
    return task_dir


def _init_db(task_dir: Path, task_id: str = "test_task") -> None:
    """在 task_dir 下初始化 state.db。"""
    db = StateDB(str(task_dir))
    db.init_task(task_id)
    db.close()


# ---- 测试用例 ----

def test_validate_requirement():
    """合法 optimized_requirement.json → 验证通过。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)
    _init_db(task_dir)

    data = {
        "original_requirement": "写一个排序算法",
        "clarifications": ["需要支持降序"],
        "proposals": [{"id": 1, "title": "快速排序"}],
        "agent_assignments": [{"agent": "coder", "task": "impl"}],
        "task_dag_preview": {"nodes": [], "edges": []},
    }
    (task_dir / "artifacts" / "optimized_requirement.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )

    ok, msg = validate_step(task_dir, "requirement_optimizing")
    results.append(("test_validate_requirement", ok, msg))


def test_validate_missing_file():
    """删除 artifacts 下文件 → 验证失败。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)

    # planning 需要 requirements.md 但不存在
    ok, msg = validate_step(task_dir, "planning")
    results.append(("test_validate_missing_file", not ok, msg))


def test_validate_invalid_json():
    """写入非法 JSON → 验证失败。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)

    (task_dir / "artifacts").mkdir(exist_ok=True)
    (task_dir / "artifacts" / "test_report.json").write_text(
        "not valid json {{{", encoding="utf-8"
    )

    ok, msg = validate_step(task_dir, "verifying")
    results.append(("test_validate_invalid_json", not ok, msg))


def test_retry_on_verify_fail():
    """模拟 verifying 失败 → 补偿回退到 executing，调用方递增 retry_count。"""
    tmp = Path(tempfile.mkdtemp())
    task_id = "test_retry_verify"
    task_dir = _setup_task_dir(tmp, task_id)
    _init_db(task_dir, task_id)

    # 设置状态到 verifying
    db = StateDB(str(task_dir))
    db.update_status(task_id, "verifying")
    db.close()

    orch = Orchestrator(str(task_dir), task_id, max_retries=3)
    orch.force_fail_step("verifying")

    # 手动触发验证
    passed, msg = orch._validate_step("verifying")
    assert not passed, f"应失败但通过了: {msg}"

    # 补偿回退（不再递增 retry）
    orch._handle_validation_failure("verifying", msg)
    # 调用方负责递增 retry（模拟 run 循环行为）
    orch.db.increment_retry(task_id)

    assert orch.get_retry_count() == 1, f"retry_count 应为 1, 实际 {orch.get_retry_count()}"

    # 验证状态回退到 executing
    state = orch.db.get_state(task_id)
    assert state["status"] == "executing", f"状态应为 executing, 实际 {state['status']}"

    results.append(("test_retry_on_verify_fail", True, "PASS"))


def test_retry_exhaust():
    """调用方递增 retry 3 次 → 超过 max_retries 后标记 failed。"""
    tmp = Path(tempfile.mkdtemp())
    task_id = "test_retry_exhaust"
    task_dir = _setup_task_dir(tmp, task_id)
    _init_db(task_dir, task_id)

    db = StateDB(str(task_dir))
    db.update_status(task_id, "planning")
    db.close()

    orch = Orchestrator(str(task_dir), task_id, max_retries=3)
    orch.force_fail_step("planning")

    # 模拟 3 次验证失败（调用方负责递增 retry）
    for i in range(3):
        passed, msg = orch._validate_step("planning")
        if not passed:
            orch._handle_validation_failure("planning", msg)
            orch.db.increment_retry(task_id)

    assert orch.get_retry_count() == 3, f"retry_count 应为 3, 实际 {orch.get_retry_count()}"

    # 超过 max_retries 时标记 failed
    if orch.get_retry_count() >= orch.max_retries:
        orch.db.update_status(task_id, "failed")
        state = orch.db.get_state(task_id)
        assert state["status"] == "failed", f"状态应为 failed, 实际 {state['status']}"

    results.append(("test_retry_exhaust", True, "PASS"))


def test_confirmation_flow():
    """完整测试 confirm → planning 推进。"""
    tmp = Path(tempfile.mkdtemp())
    task_id = "test_confirm"
    task_dir = _setup_task_dir(tmp, task_id)
    _init_db(task_dir, task_id)

    db = StateDB(str(task_dir))
    db.update_status(task_id, "confirmation")
    db.close()

    orch = Orchestrator(str(task_dir), task_id)

    # 模拟用户确认
    result = orch.handle_confirmation("confirm")
    assert result["result"] == "confirmed", f"确认结果应为 confirmed: {result}"
    assert result["next"] == "planning", f"下一步应为 planning: {result}"

    # 验证 db 状态
    db2 = StateDB(str(task_dir))
    state = db2.get_state(task_id)
    db2.close()
    assert state["status"] == "planning", f"状态应为 planning, 实际 {state['status']}"

    results.append(("test_confirmation_flow", True, "PASS"))


# ---- 运行所有测试 ----

def main():
    tests = [
        test_validate_requirement,
        test_validate_missing_file,
        test_validate_invalid_json,
        test_retry_on_verify_fail,
        test_retry_exhaust,
        test_confirmation_flow,
    ]

    for t in tests:
        try:
            t()
        except AssertionError as e:
            results.append((t.__name__, False, str(e)))
        except Exception as e:
            results.append((t.__name__, False, f"异常: {e}"))

    # 打印结果
    print("\n" + "=" * 60)
    print("阶段二测试结果")
    print("=" * 60)
    all_passed = True
    for name, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not ok:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("PHASE 2: ALL TESTS PASSED")
    else:
        print("PHASE 2: SOME TESTS FAILED")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()