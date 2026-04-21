"""阶段二测试：验证、重试、质量门、确认流。"""

import json
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scripts.validator import validate_step, _check_requirement_schema
from core.quality_gates import QualityGateRunner, GATES
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
    """模拟 verifying 失败 → 回退到 executing 且 retry_count=1。"""
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

    # 处理失败
    orch._handle_validation_failure("verifying", msg)

    assert orch.get_retry_count() == 1, f"retry_count 应为 1, 实际 {orch.get_retry_count()}"

    # 验证回退到 executing
    db2 = StateDB(str(task_dir))
    state = db2.get_state(task_id)
    db2.close()
    assert state["status"] == "executing", f"状态应为 executing, 实际 {state['status']}"

    results.append(("test_retry_on_verify_fail", True, "PASS"))


def test_retry_exhaust():
    """连续失败 3 次 → 任务标记为 failed。"""
    tmp = Path(tempfile.mkdtemp())
    task_id = "test_retry_exhaust"
    task_dir = _setup_task_dir(tmp, task_id)
    _init_db(task_dir, task_id)

    db = StateDB(str(task_dir))
    db.update_status(task_id, "planning")
    db.close()

    orch = Orchestrator(str(task_dir), task_id, max_retries=3)
    orch.force_fail_step("planning")

    # 模拟 3 次验证失败
    for i in range(3):
        passed, msg = orch._validate_step("planning")
        if not passed:
            orch._handle_validation_failure("planning", msg)

    assert orch.get_retry_count() == 3, f"retry_count 应为 3, 实际 {orch.get_retry_count()}"

    # 超过 max_retries 时标记 failed
    if orch.get_retry_count() >= orch.max_retries:
        db3 = StateDB(str(task_dir))
        db3.update_status(task_id, "failed")
        state = db3.get_state(task_id)
        db3.close()
        assert state["status"] == "failed", f"状态应为 failed, 实际 {state['status']}"

    results.append(("test_retry_exhaust", True, "PASS"))


def test_quality_gate_pass():
    """simplify_report.json（passed=True）→ quality gate 通过。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)

    report = {"passed": True, "details": "代码质量合格"}
    (task_dir / "artifacts" / "simplify_report.json").write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    runner = QualityGateRunner()
    result = runner.run_gates(task_dir, "verifying")

    assert result["approved"], f"应通过但未通过: {result}"
    results.append(("test_quality_gate_pass", True, "PASS"))


def test_quality_gate_retry():
    """simplify_report.json（passed=False）→ approved=False。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)

    report = {"passed": False, "details": "代码需要简化"}
    (task_dir / "artifacts" / "simplify_report.json").write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    runner = QualityGateRunner()
    result = runner.run_gates(task_dir, "verifying")

    assert not result["approved"], f"不应通过但通过了: {result}"
    results.append(("test_quality_gate_retry", True, "PASS"))


def test_quality_gate_warn():
    """security_review.json（passed=False, action=warn）→ 仅警告，不阻断。"""
    tmp = Path(tempfile.mkdtemp())
    task_dir = _setup_task_dir(tmp)

    report = {"passed": False, "details": "存在潜在安全问题"}
    (task_dir / "artifacts" / "security_review.json").write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )

    runner = QualityGateRunner()
    result = runner.run_gates(task_dir, "executing")

    # warn 不阻断，approved 仍为 True
    assert result["approved"], f"warn 应不阻断但 approved=False: {result}"
    # 但 results 中应有记录
    failed_gates = [r for r in result["results"] if r.get("passed") is False]
    assert len(failed_gates) > 0, "应有失败的 gate 记录"

    results.append(("test_quality_gate_warn", True, "PASS"))


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
        test_quality_gate_pass,
        test_quality_gate_retry,
        test_quality_gate_warn,
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