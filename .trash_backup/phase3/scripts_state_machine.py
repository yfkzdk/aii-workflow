"""状态机 — 增强版，支持输入收集、需求优化、用户确认门、任务DAG"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from utils import atomic_write_json

# 增强版管线：新增 input_collecting, requirement_optimizing, confirmation
ENHANCED_PIPELINE = [
    "input_collecting",
    "requirement_optimizing",
    "confirmation",
    "planning",
    "prompt_optimizing",
    "executing",
    "verifying",
    "archiving",
    "completed"
]

LEGACY_PIPELINE = [
    "planning",
    "prompt_optimizing",
    "executing",
    "verifying",
    "archiving",
    "completed"
]


def _safe_step_index(pipeline: list, step_name: str) -> int:
    """安全的步进索引：找到返回位置，未找到则指向管线末尾（非 99）"""
    if step_name in pipeline:
        return pipeline.index(step_name)
    return len(pipeline) - 1


def init_state(task_dir: str, task_id: str, enhanced: bool = True):
    """初始化状态机，enhanced=True使用增强管线"""
    sf = Path(task_dir) / "state.json"
    Path(task_dir).mkdir(parents=True, exist_ok=True)
    (Path(task_dir) / "artifacts").mkdir(exist_ok=True)

    pipeline = ENHANCED_PIPELINE if enhanced else LEGACY_PIPELINE
    initial_status = pipeline[0]

    st = {
        "task_id": task_id,
        "status": initial_status,
        "pipeline": pipeline,
        "current_step_index": 0,
        "retry_count": 0,
        "max_retries": 3,
        "next_agent": "input_collector" if enhanced else "planner",
        "checkpoint": {},
        "user_input": {
            "chunks": [],
            "is_complete": False,
            "completed_at": None
        },
        "task_dag": None,
        "skill_usage_log": [],
        "confirmation": {
            "status": "pending",  # pending, confirmed, revised, rejected
            "selected_proposal": None,
            "user_skill_overrides": {},
            "clarification_updates": [],
            "confirmed_at": None
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    atomic_write_json(sf, st)
    mode = "增强" if enhanced else "经典"
    print(f"[INIT] 状态机初始化({mode}): {task_dir}")
    print(f"       管线: {' → '.join(pipeline)}")


def update_state(task_dir: str, current: str, next_state: str, next_agent: str):
    """原始状态更新（无校验）"""
    sf = Path(task_dir) / "state.json"
    if not sf.exists():
        print("[ERROR] state.json missing")
        return

    with open(sf, 'r', encoding='utf-8') as f:
        st = json.load(f)

    st["status"] = next_state
    st["next_agent"] = next_agent if next_agent != "null" else None
    pipeline = st.get("pipeline", LEGACY_PIPELINE)
    st["current_step_index"] = _safe_step_index(pipeline, next_state)
    st["updated_at"] = datetime.now().isoformat()
    atomic_write_json(sf, st)
    print(f"[OK] 状态流转: {current} -> {next_state}")


def safe_transition(task_dir: str, current: str, next_step: str, next_agent: str, force: bool = False) -> bool:
    """安全状态流转：校验通过才推进"""
    sf = Path(task_dir) / "state.json"
    if not sf.exists():
        print("[ERROR] state.json missing")
        return False

    with open(sf, 'r', encoding='utf-8') as f:
        st = json.load(f)

    # 尝试导入验证器
    try:
        from validator import validate_step
        validation_available = True
    except ImportError:
        validation_available = False

    # 非强制模式下必须通过校验
    if not force and validation_available:
        valid, msg = validate_step(Path(task_dir), current)
        if not valid:
            st["validation_status"] = "FAILED"
            st["validation_error"] = msg
            st["retry_count"] = st.get("retry_count", 0) + 1
            st["updated_at"] = datetime.now().isoformat()
            atomic_write_json(sf, st)
            print(f"[WARN] 校验失败 [{current}]: {msg} | 重试 {st['retry_count']}/{st.get('max_retries',3)}")
            return False
        st["validation_status"] = "PASSED"

    st["status"] = next_step
    st["next_agent"] = next_agent
    pipeline = st.get("pipeline", LEGACY_PIPELINE)
    st["current_step_index"] = _safe_step_index(pipeline, next_step)
    st["updated_at"] = datetime.now().isoformat()
    atomic_write_json(sf, st)
    print(f"[OK] 安全流转: {current} -> {next_step} | 校验: {'PASS' if validation_available else 'SKIP'}")
    return True


def confirm_transition(task_dir: str, user_response: Dict[str, Any]) -> str:
    """
    处理用户确认门的决策

    Args:
        task_dir: 任务目录
        user_response: 用户决策
            {"action": "confirm", "selected_proposal": "B", "skill_overrides": {}, "clarification_updates": []}
            {"action": "revise", "clarification_updates": [...]}
            {"action": "reject"}

    Returns:
        结果状态: "confirmed", "revised", "cancelled", "error"
    """
    sf = Path(task_dir) / "state.json"
    if not sf.exists():
        print("[ERROR] state.json missing")
        return "error"

    with open(sf, 'r', encoding='utf-8') as f:
        st = json.load(f)

    if st.get("status") != "confirmation":
        print(f"[ERROR] 当前状态不是confirmation，而是 {st['status']}")
        return "error"

    action = user_response.get("action")

    if action == "confirm":
        # 锁定方案，进入planning
        st["confirmation"]["status"] = "confirmed"
        st["confirmation"]["selected_proposal"] = user_response.get("selected_proposal")
        st["confirmation"]["user_skill_overrides"] = user_response.get("skill_overrides", {})
        st["confirmation"]["clarification_updates"] = user_response.get("clarification_updates", [])
        st["confirmation"]["confirmed_at"] = datetime.now().isoformat()
        st["status"] = "planning"
        st["next_agent"] = "planner"
        pipeline = st.get("pipeline", ENHANCED_PIPELINE)
        st["current_step_index"] = _safe_step_index(pipeline, "planning")
        st["updated_at"] = datetime.now().isoformat()
        atomic_write_json(sf, st)
        print(f"[OK] 用户确认 → 进入 planning (方案: {user_response.get('selected_proposal')})")
        return "confirmed"

    elif action == "revise":
        # 用户修改，回到requirement_optimizing
        st["confirmation"]["status"] = "revised"
        st["confirmation"]["clarification_updates"] = user_response.get("clarification_updates", [])
        st["status"] = "requirement_optimizing"
        st["next_agent"] = "requirement_optimizer"
        pipeline = st.get("pipeline", ENHANCED_PIPELINE)
        st["current_step_index"] = _safe_step_index(pipeline, "requirement_optimizing")
        st["updated_at"] = datetime.now().isoformat()
        atomic_write_json(sf, st)
        print(f"[OK] 用户修改 → 回到 requirement_optimizing 重新优化")
        return "revised"

    elif action == "reject":
        # 用户拒绝，任务取消
        st["confirmation"]["status"] = "rejected"
        st["status"] = "cancelled"
        st["next_agent"] = None
        st["current_step_index"] = len(st.get("pipeline", ENHANCED_PIPELINE)) - 1
        st["updated_at"] = datetime.now().isoformat()
        atomic_write_json(sf, st)
        print(f"[OK] 用户拒绝 → 任务取消")
        return "cancelled"

    else:
        print(f"[ERROR] 未知action: {action}")
        return "error"


def parse_user_response(response_str: str) -> Dict[str, Any]:
    """
    解析用户自然语言回复（支持中文）

    Args:
        response_str: 用户回复文本

    Returns:
        解析后的决策字典
    """
    text = response_str.strip().lower()

    # 1. 拒绝
    reject_patterns = ["取消", "不要了", "放弃", "cancel", "reject", "不用了", "算了"]
    for pattern in reject_patterns:
        if pattern in text:
            return {
                "action": "reject",
                "selected_proposal": None,
                "clarification_updates": [],
                "raw_response": response_str
            }

    # 2. 修改澄清
    if "修改" in text or ":" in text or "改为" in text or "换成" in text:
        updates = []

        # 尝试解析冒号格式: "修改 联机方式: HTTP轮询"
        if ":" in text:
            parts = text.split(":")
            if len(parts) >= 2:
                point = parts[0].replace("修改", "").strip()
                value = parts[1].strip()
                updates.append({"point": point, "new_value": value})

        # 尝试解析"改为"格式: "联机方式改为HTTP轮询"
        elif "改为" in text or "换成" in text:
            for keyword in ["改为", "换成"]:
                if keyword in text:
                    parts = text.split(keyword)
                    if len(parts) >= 2:
                        point = parts[0].replace("修改", "").strip()
                        value = parts[1].strip()
                        updates.append({"point": point, "new_value": value})
                        break

        if updates:
            return {
                "action": "revise",
                "selected_proposal": None,
                "clarification_updates": updates,
                "raw_response": response_str
            }

    # 3. 确认方案
    # 匹配: confirm A, 选B, 方案B, B, 用B, 确认B
    confirm_patterns = [
        ("confirm a", "A"),
        ("confirm b", "B"),
        ("confirm c", "C"),
        ("选a", "A"),
        ("选b", "B"),
        ("选c", "C"),
        ("方案a", "A"),
        ("方案b", "B"),
        ("方案c", "C"),
        ("用a", "A"),
        ("b", "B"),
        ("用c", "C"),
        ("确认a", "A"),
        ("确认b", "B"),
        ("确认c", "C"),
    ]

    for pattern, proposal_id in confirm_patterns:
        if pattern in text:
            return {
                "action": "confirm",
                "selected_proposal": proposal_id,
                "clarification_updates": [],
                "raw_response": response_str
            }

    # 单字母匹配
    if text in ["a", "b", "c"]:
        return {
            "action": "confirm",
            "selected_proposal": text.upper(),
            "clarification_updates": [],
            "raw_response": response_str
        }

    # 4. 默认确认（如果是肯定的回复）
    positive_patterns = ["确认", "好的", "可以", "没问题", "ok", "yes", "confirm", "是"]
    for pattern in positive_patterns:
        if pattern in text:
            return {
                "action": "confirm",
                "selected_proposal": "B",  # 默认选择标准方案
                "clarification_updates": [],
                "raw_response": response_str
            }

    # 5. 无法解析
    return {
        "action": "unknown",
        "selected_proposal": None,
        "clarification_updates": [],
        "raw_response": response_str,
        "error": "无法解析用户回复，请使用: confirm A/B/C 或 修改 <澄清项>: <新值>"
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  init <task_dir> <task_id> [enhanced=true/false]")
        print("  update <task_dir> <current> <next_state> <next_agent>")
        print("  safe_update <task_dir> <current> <next_step> <next_agent> [force]")
        print("  confirm <task_dir> <confirm|revise|reject> [proposal] [overrides_json]")
        print("  confirm <task_dir> parse \"<natural_language_response>\"")
        print("  parse \"<response_str>\"")
        sys.exit(0)

    cmd, *args = sys.argv[1:]

    if cmd == "init":
        # init <task_dir> <task_id> [enhanced=true/false]
        enhanced = True
        if len(args) > 2:
            enhanced = args[2].lower() != "false"
        init_state(args[0], args[1], enhanced)

    elif cmd == "update":
        # update <task_dir> <current> <next_state> <next_agent>
        update_state(*args)

    elif cmd == "safe_update":
        # safe_update <task_dir> <current> <next_step> <next_agent> [force]
        if len(args) >= 4:
            force = len(args) > 4 and args[4].lower() == "true"
            success = safe_transition(args[0], args[1], args[2], args[3], force)
            if not success:
                print("[ERROR] 安全流转失败")
        else:
            print("[ERROR] 参数不足: safe_update <task_dir> <current> <next_step> <next_agent> [force]")

    elif cmd == "confirm":
        # confirm <task_dir> <action> [selected_proposal] [skill_overrides_json]
        # confirm <task_dir> parse "<natural_language_response>"
        if len(args) < 2:
            print("[ERROR] 参数不足: confirm <task_dir> <action|parse> [proposal] [overrides_json]")
            sys.exit(1)

        task_dir = args[0]
        action = args[1]

        # 新增: 解析自然语言
        if action == "parse":
            if len(args) < 3:
                print("[ERROR] 参数不足: confirm <task_dir> parse \"<response>\"")
                sys.exit(1)

            response_str = args[2]
            parsed = parse_user_response(response_str)
            print(json.dumps(parsed, ensure_ascii=False, indent=2))

            if parsed.get("action") not in ["unknown"]:
                # 直接执行确认门转换
                result = confirm_transition(task_dir, parsed)
                print(f"[RESULT] {result}")
            else:
                print(f"[ERROR] {parsed.get('error', '无法解析')}")
            sys.exit(0)

        # 原有 JSON 参数方式
        response = {"action": action}

        if action == "confirm":
            response["selected_proposal"] = args[2] if len(args) > 2 else "B"
            if len(args) > 3:
                try:
                    response["skill_overrides"] = json.loads(args[3])
                except json.JSONDecodeError:
                    response["skill_overrides"] = {}

        elif action == "revise":
            if len(args) > 2:
                try:
                    response["clarification_updates"] = json.loads(args[2])
                except json.JSONDecodeError:
                    response["clarification_updates"] = []

        result = confirm_transition(task_dir, response)

    elif cmd == "parse":
        # parse "<response_str>" - 独立解析命令
        if len(args) < 1:
            print("[ERROR] 参数不足: parse \"<response>\"")
            sys.exit(1)

        response_str = " ".join(args)
        result = parse_user_response(response_str)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print("可用命令:")
        print("  init <task_dir> <task_id> [enhanced=true/false]")
        print("  update <task_dir> <current> <next_state> <next_agent>")
        print("  safe_update <task_dir> <current> <next_step> <next_agent> [force]")
        print("  confirm <task_dir> <confirm|revise|reject> [proposal] [overrides_json]")
        print("  confirm <task_dir> parse \"<natural_language_response>\"")
        print("  parse \"<response_str>\"")