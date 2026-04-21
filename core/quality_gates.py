"""QualityGateRunner -- 质量门检查器。

阶段二只检查产出文件是否存在及 passed 字段，
不实现 skill 的自动调用（那是 Claude Code 运行时的事）。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


GATES: Dict[str, List[Dict[str, str]]] = {
    "executing": [{"skill": "security-review", "action": "warn"}],
    "verifying": [{"skill": "simplify", "action": "retry"}],
    "archiving": [{"skill": "review", "action": "log"}],
}

_SKILL_FILES = {
    "security-review": "security_review.json",
    "simplify": "simplify_report.json",
    "review": "review_report.json",
}


class QualityGateRunner:
    """检查 artifacts/ 下 skill 输出文件，判断是否通过质量门。"""

    def __init__(self, gates: Optional[Dict[str, List[Dict[str, str]]]] = None):
        self.gates = gates if gates is not None else GATES

    def run_gates(self, task_dir: Path, step: str) -> Dict[str, Any]:
        """执行指定步骤的质量门检查。

        返回 {"approved": bool, "results": [...]}
        每条 result: {"skill": str, "action": str, "passed": bool|None, "reason": str}
        """
        gate_list = self.gates.get(step, [])
        if not gate_list:
            return {"approved": True, "results": []}

        artifacts = task_dir / "artifacts"
        results: List[Dict[str, Any]] = []
        approved = True

        for gate in gate_list:
            skill = gate["skill"]
            action = gate["action"]
            filename = _SKILL_FILES.get(skill, f"{skill}.json")
            filepath = artifacts / filename

            if not filepath.exists():
                results.append({
                    "skill": skill, "action": action,
                    "passed": None, "reason": "跳过(文件不存在)",
                })
                continue

            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
            except Exception as e:
                results.append({
                    "skill": skill, "action": action,
                    "passed": None, "reason": f"JSON解析失败: {e}",
                })
                continue

            passed = data.get("passed") is True

            if passed:
                results.append({
                    "skill": skill, "action": action,
                    "passed": True, "reason": "通过",
                })
            else:
                results.append({
                    "skill": skill, "action": action,
                    "passed": False,
                    "reason": f"未通过 (passed={data.get('passed')})",
                })
                if action == "retry":
                    approved = False

        return {"approved": approved, "results": results}