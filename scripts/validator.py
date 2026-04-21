import json, os, py_compile, sqlite3, sys
from pathlib import Path

_REQUIREMENT_FIELDS = [
    "original_requirement", "clarifications",
    "proposals", "agent_assignments", "task_dag_preview",
]


def validate_step(task_dir: Path, step: str) -> tuple[bool, str]:
    """轻量级结构校验，失败返回具体原因"""
    artifacts = task_dir / "artifacts"

    checks = {
        "requirement_optimizing": lambda: _check_requirement_schema(
            artifacts / "optimized_requirement.json"
        ),
        "input_collecting": lambda: _check_input_collecting(task_dir),
        "confirmation": lambda: _check_confirmation(task_dir),
        "planning": lambda: _check_file(artifacts / "requirements.md", min_len=10),
        "prompt_optimizing": lambda: _check_file(artifacts / "optimal_prompt.md", min_len=10),
        "executing": lambda: _check_code(artifacts / "code"),
        "verifying": lambda: _check_test_report(artifacts / "test_report.json"),
        "archiving": lambda: _check_file(task_dir / "AI_WORKFLOW_LOG.md", min_len=1),
    }

    checker = checks.get(step)
    if not checker:
        return False, f"未知步骤: {step}"
    return checker()


def _check_json(path: Path):
    if not path.exists():
        return False, f"缺失: {path.name}"
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, "PASS"
    except Exception as e:
        return False, f"JSON格式错误: {e}"


def _check_file(path: Path, min_len: int = 10):
    if not path.exists():
        return False, f"缺失: {path.name}"
    content = path.read_text(encoding="utf-8")
    if len(content) < min_len:
        return False, f"内容过短({len(content)}字符)"
    return True, "PASS"


def _check_code(code_dir: Path):
    if not code_dir.exists() or not list(code_dir.glob("*.py")):
        return False, "artifacts/code/ 下无 Python 文件"
    for py in code_dir.glob("*.py"):
        try:
            py_compile.compile(str(py), doraise=True)
        except py_compile.PyCompileError as e:
            return False, f"语法错误 {py.name}: {e.msg}"
    return True, "PASS"


def _check_requirement_schema(path: Path):
    """校验 optimized_requirement.json 存在、合法 JSON、含必需字段。"""
    if not path.exists():
        return False, f"缺失: {path.name}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"JSON格式错误: {e}"
    missing = [f for f in _REQUIREMENT_FIELDS if f not in data]
    if missing:
        return False, f"缺少必需字段: {', '.join(missing)}"
    return True, "PASS"


def _check_input_collecting(task_dir: Path):
    """校验 state.db 中 user_input 不为空且 is_complete=True。"""
    db_path = task_dir / "state.db"
    if not db_path.exists():
        return False, "缺失: state.db"
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT user_input_json FROM task_state LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception as e:
        return False, f"state.db 读取失败: {e}"
    if row is None:
        return False, "state.db 无任务记录"
    try:
        user_input = json.loads(row["user_input_json"])
    except Exception:
        return False, "user_input_json 解析失败"
    if not user_input or not user_input.get("chunks"):
        return False, "user_input 为空"
    if not user_input.get("is_complete"):
        return False, "user_input 尚未完成 (is_complete != True)"
    return True, "PASS"


def _check_confirmation(task_dir: Path):
    """校验 confirmation.status == 'confirmed'。"""
    db_path = task_dir / "state.db"
    if not db_path.exists():
        return False, "缺失: state.db"
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT confirmation_json FROM task_state LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception as e:
        return False, f"state.db 读取失败: {e}"
    if row is None:
        return False, "state.db 无任务记录"
    try:
        confirmation = json.loads(row["confirmation_json"])
    except Exception:
        return False, "confirmation_json 解析失败"
    if confirmation.get("status") != "confirmed":
        return False, f"确认状态为 '{confirmation.get('status')}', 需要 'confirmed'"
    return True, "PASS"


def _check_test_report(path: Path):
    """校验 test_report.json 存在且 status 为 PASS 或 FAIL。"""
    ok, msg = _check_json(path)
    if not ok:
        return ok, msg
    data = json.loads(path.read_text(encoding="utf-8"))
    status = data.get("status", "")
    if status not in ("PASS", "FAIL"):
        return False, f"test_report status='{status}', 需要 PASS 或 FAIL"
    return True, "PASS"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python validator.py <task_dir> <step>")
        print("Steps: requirement_optimizing, input_collecting, confirmation, "
              "planning, prompt_optimizing, executing, verifying, archiving")
        sys.exit(1)

    task_dir = Path(sys.argv[1])
    step = sys.argv[2]
    valid, msg = validate_step(task_dir, step)
    print(f"[{'PASS' if valid else 'FAIL'}] {step}: {msg}")
    sys.exit(0 if valid else 1)