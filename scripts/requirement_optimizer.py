"""需求优化引擎 — 精简版（无硬编码推理）

此模块提供：
- validate_output: 校验优化结果是否符合 Schema
- get_full_input: 获取完整用户输入
- save_placeholder: 生成空模板供 Agent 填充

所有推理逻辑由 requirement_optimizer.md 中的 Agent 指令执行，不在此硬编码。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.db import StateDB


def get_full_input(task_dir: str) -> str:
    """
    获取完整用户输入（从 StateDB 读取）

    Args:
        task_dir: 任务目录路径

    Returns:
        拼接后的完整用户输入文本
    """
    db_path = Path(task_dir) / "state.db"
    if not db_path.exists():
        return ""

    try:
        db = StateDB(task_dir)
        task_id = Path(task_dir).name
        state = db.get_state(task_id)
        db.close()
    except (ValueError, Exception):
        return ""

    user_input_json = state.get("user_input_json", "{}")
    try:
        user_input = json.loads(user_input_json) if isinstance(user_input_json, str) else user_input_json
    except json.JSONDecodeError:
        return ""

    chunks = user_input.get("chunks", [])

    if not chunks:
        return ""

    sorted_chunks = sorted(chunks, key=lambda x: x.get("seq", 0))
    return "\n\n".join(chunk.get("content", "") for chunk in sorted_chunks)


def load_schema() -> Dict[str, Any]:
    """加载 requirement_schema.json"""
    schema_path = Path(__file__).parent.parent / "config" / "requirement_schema.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_output(task_dir: str) -> Dict[str, Any]:
    """
    校验 artifacts/optimized_requirement.json 是否符合 Schema

    Args:
        task_dir: 任务目录路径

    Returns:
        {"valid": True/False, "errors": [...], "warnings": [...]}
    """
    output_file = Path(task_dir) / "artifacts" / "optimized_requirement.json"
    result = {"valid": False, "errors": [], "warnings": []}

    if not output_file.exists():
        result["errors"].append(f"Output file not found: {output_file}")
        return result

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON: {e}")
        return result

    schema = load_schema()

    # 基本校验：必填字段
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            result["errors"].append(f"Missing required field: {field}")

    if result["errors"]:
        return result

    # 校验 clarifications
    clarifications = data.get("clarifications", [])
    for i, c in enumerate(clarifications):
        if c.get("confidence", 1) < 0.8 and not c.get("needs_user_confirm"):
            result["warnings"].append(
                f"Clarification[{i}] has confidence < 0.8 but needs_user_confirm=False"
            )

    # 校验 proposals
    proposals = data.get("proposals", [])
    if len(proposals) < 2:
        result["errors"].append("At least 2 proposals required")
    elif len(proposals) > 3:
        result["errors"].append("At most 3 proposals allowed")

    proposal_ids = [p.get("id") for p in proposals]
    if "A" not in proposal_ids or "B" not in proposal_ids:
        result["errors"].append("Proposals must include A (minimal) and B (standard)")

    # 校验复杂度与方案C的关系
    features = data.get("features_detected", {})
    complexity = features.get("complexity_score", 0)
    if "C" in proposal_ids and complexity < 1.5:
        result["warnings"].append(
            f"Proposal C provided but complexity_score={complexity} < 1.5"
        )
    if complexity >= 1.5 and "C" not in proposal_ids:
        result["warnings"].append(
            f"complexity_score={complexity} >= 1.5 but no Proposal C"
        )

    # 校验 agent_assignments
    assignments = data.get("agent_assignments", [])
    required_agents = {"planner", "verifier", "archivist"}
    assigned_agents = {a.get("agent_id") for a in assignments}

    missing = required_agents - assigned_agents
    if missing:
        result["errors"].append(f"Missing required agents: {missing}")

    # 校验并行关系一致性
    for a in assignments:
        parallel_with = a.get("parallel_with")
        if parallel_with:
            # 检查被并行的 Agent 是否存在
            if parallel_with not in assigned_agents:
                result["errors"].append(
                    f"Agent {a.get('agent_id')} parallel_with={parallel_with}, but {parallel_with} not assigned"
                )

    # 校验 task_dag_preview
    dag = data.get("task_dag_preview", {})
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])

    for edge in edges:
        if len(edge) != 2:
            result["errors"].append(f"Invalid edge format: {edge}")
        else:
            from_node, to_node = edge
            if from_node not in nodes:
                result["errors"].append(f"Edge references unknown node: {from_node}")
            if to_node not in nodes:
                result["errors"].append(f"Edge references unknown node: {to_node}")

    # 校验 parallel_groups
    parallel_groups = dag.get("parallel_groups", [])
    for group in parallel_groups:
        for node in group:
            if node not in nodes:
                result["errors"].append(f"Parallel group references unknown node: {node}")

    # 校验 skills 来源
    for proposal in proposals:
        for skill_rec in proposal.get("skills_recommended", []):
            for skill in skill_rec.get("skills", []):
                source = skill.get("source")
                if source not in ["auto_match", "user_specified", "default"]:
                    result["warnings"].append(
                        f"Unknown skill source: {source}"
                    )

    result["valid"] = len(result["errors"]) == 0
    return result


def save_placeholder(task_dir: str) -> str:
    """
    生成空的优化结果模板供 Agent 填充

    Args:
        task_dir: 任务目录路径

    Returns:
        输出文件路径
    """
    artifacts_dir = Path(task_dir) / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    placeholder = {
        "original_requirement": "",
        "clarifications": [],
        "proposals": [
            {
                "id": "A",
                "name": "最小可行方案",
                "description": "核心功能实现，无额外扩展",
                "scope": "minimal",
                "estimated_tasks": 0,
                "skills_recommended": [],
                "pros": [],
                "cons": []
            },
            {
                "id": "B",
                "name": "标准方案",
                "description": "完整实现需求，适度扩展",
                "scope": "standard",
                "estimated_tasks": 0,
                "skills_recommended": [],
                "pros": [],
                "cons": []
            }
        ],
        "agent_assignments": [],
        "task_dag_preview": {
            "nodes": [],
            "edges": [],
            "parallel_groups": []
        },
        "features_detected": {
            "has_frontend": {"detected": False, "evidence": None},
            "has_backend": {"detected": False, "evidence": None},
            "has_ai": {"detected": False, "evidence": None},
            "has_network": {"detected": False, "evidence": None},
            "has_security": {"detected": False, "evidence": None},
            "has_game": {"detected": False, "evidence": None},
            "complexity_score": 0.0,
            "domain_tags": []
        },
        "reasoning_trace": {
            "feature_analysis": "",
            "proposal_decision": "",
            "skill_matching_logic": "",
            "agent_assignment_rationale": ""
        },
        "optimized_at": datetime.now().isoformat()
    }

    output_path = artifacts_dir / "optimized_requirement.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(placeholder, f, indent=2, ensure_ascii=False)

    return str(output_path)


def load_optimization(task_dir: str) -> Optional[Dict[str, Any]]:
    """
    加载已保存的优化结果

    Args:
        task_dir: 任务目录路径

    Returns:
        优化结果字典，若不存在返回 None
    """
    output_file = Path(task_dir) / "artifacts" / "optimized_requirement.json"

    if not output_file.exists():
        return None

    with open(output_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_selected_proposal(task_dir: str) -> Optional[Dict[str, Any]]:
    """
    获取用户选择的方案（从 StateDB 读取）

    Args:
        task_dir: 任务目录路径

    Returns:
        选中的方案字典，若未确认返回 None
    """
    db_path = Path(task_dir) / "state.db"
    if not db_path.exists():
        return None

    try:
        db = StateDB(task_dir)
        task_id = Path(task_dir).name
        state = db.get_state(task_id)
        db.close()
    except (ValueError, Exception):
        return None

    confirmation_json = state.get("confirmation_json", "{}")
    try:
        confirmation = json.loads(confirmation_json) if isinstance(confirmation_json, str) else confirmation_json
    except json.JSONDecodeError:
        return None

    selected_id = confirmation.get("selected_proposal")

    if not selected_id:
        return None

    optimization = load_optimization(task_dir)
    if not optimization:
        return None

    for proposal in optimization.get("proposals", []):
        if proposal.get("id") == selected_id:
            return proposal

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Available commands:")
        print("  validate <task_dir>    - Validate optimization output against schema")
        print("  get_input <task_dir>   - Get full user input")
        print("  placeholder <task_dir> - Create empty template for Agent to fill")
        print("  load <task_dir>        - Load saved optimization")
        sys.exit(0)

    cmd, *args = sys.argv[1:]

    if cmd == "validate":
        # validate <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python requirement_optimizer.py validate <task_dir>")
            sys.exit(1)

        result = validate_output(args[0])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["valid"] else 1)

    elif cmd == "get_input":
        # get_input <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python requirement_optimizer.py get_input <task_dir>")
            sys.exit(1)

        raw_input = get_full_input(args[0])
        print(raw_input)

    elif cmd == "placeholder":
        # placeholder <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python requirement_optimizer.py placeholder <task_dir>")
            sys.exit(1)

        output_path = save_placeholder(args[0])
        print(json.dumps({"status": "created", "path": output_path}, ensure_ascii=False))

    elif cmd == "load":
        # load <task_dir>
        if len(args) < 1:
            print("[ERROR] Usage: python requirement_optimizer.py load <task_dir>")
            sys.exit(1)

        data = load_optimization(args[0])
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("[ERROR] No optimization found")

    else:
        print("[ERROR] Unknown command:", cmd)
        print("Available commands:")
        print("  validate <task_dir>    - Validate optimization output against schema")
        print("  get_input <task_dir>   - Get full user input")
        print("  placeholder <task_dir> - Create empty template for Agent to fill")
        print("  load <task_dir>        - Load saved optimization")
        sys.exit(1)