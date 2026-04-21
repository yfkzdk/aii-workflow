"""Skill管理器 — 权限检查、调用和性能更新"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


from utils import atomic_write_json


class SkillManager:
    """Skill管理：权限检查、调用准备、性能更新"""

    def __init__(self, task_dir: str = None, agent_id: str = None):
        self.task_dir = Path(task_dir) if task_dir else None
        self.agent_id = agent_id
        self.registry = self._load_registry()
        self.agent_skills = []
        self.usage_log = []

        if task_dir and agent_id:
            self.agent_skills = self._load_agent_skills()

    def _load_registry(self) -> dict:
        """加载skill注册表"""
        base_dir = Path(__file__).parent.parent
        registry_path = base_dir / "config" / "skills.json"
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"skill_registry": {}, "global_skills": []}

    def _load_agent_skills(self) -> List[str]:
        """从manifest加载agent的skill白名单"""
        base_dir = Path(__file__).parent.parent
        manifest_path = base_dir / ".claude" / "agents" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            agent_profile = manifest.get("agents", {}).get(self.agent_id, {})
            return agent_profile.get("skills", [])
        return []

    def can_use(self, skill_id: str) -> tuple:
        """
        检查agent是否有权限使用该skill

        Returns:
            (bool, str): (是否允许, 原因)
        """
        # 检查全局skills
        if skill_id in self.registry.get("global_skills", []):
            return True, "全局skill"

        # 检查agent专属skills
        if skill_id in self.agent_skills:
            return True, "agent专属skill"

        # 检查skill是否存在
        if skill_id not in self.registry.get("skill_registry", {}):
            return False, f"未知skill: {skill_id}"

        return False, f"Agent {self.agent_id} 无权使用 {skill_id}"

    def invoke(self, skill_id: str, args: dict = None) -> dict:
        """
        准备skill调用

        Returns:
            包含skill执行所需信息的字典
        """
        allowed, reason = self.can_use(skill_id)
        if not allowed:
            return {"error": reason, "status": "denied"}

        skill_meta = self.registry.get("skill_registry", {}).get(skill_id, {})
        if not skill_meta:
            return {"error": f"未知skill: {skill_id}", "status": "not_found"}

        return {
            "skill_id": skill_id,
            "status": "ready",
            "description": skill_meta.get("description", ""),
            "permissions": skill_meta.get("permissions", []),
            "estimated_cost": skill_meta.get("estimated_cost", "unknown"),
            "args": args or {},
            "invoked_at": datetime.now().isoformat()
        }

    def record_usage(self, skill_id: str, source: str, outcome: str,
                     duration_seconds: float, token_cost: int = 0,
                     user_override: bool = False, user_replaced: str = None):
        """记录skill使用情况"""
        record = {
            "skill_id": skill_id,
            "source": source,  # "auto_match" or "user_specified"
            "outcome": outcome,  # "success" or "failed"
            "duration_seconds": duration_seconds,
            "token_cost": token_cost,
            "user_override": user_override,
            "user_replaced": user_replaced,
            "recorded_at": datetime.now().isoformat()
        }
        self.usage_log.append(record)

        # 如果有task_dir，立即写入state.json
        if self.task_dir:
            self._append_usage_to_state(record)

    def _append_usage_to_state(self, record: dict):
        """将usage记录追加到state.json"""
        state_file = self.task_dir / "state.json"
        if not state_file.exists():
            return

        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        if "skill_usage_log" not in state:
            state["skill_usage_log"] = []
        state["skill_usage_log"].append(record)
        state["updated_at"] = datetime.now().isoformat()

        atomic_write_json(state_file, state)

    def update_skill_performance(self):
        """用当前任务的usage数据更新skill registry的性能档案"""
        if not self.usage_log:
            return

        base_dir = Path(__file__).parent.parent
        registry_path = base_dir / "config" / "skills.json"

        for record in self.usage_log:
            skill_id = record["skill_id"]
            if skill_id not in self.registry.get("skill_registry", {}):
                continue

            profile = self.registry["skill_registry"][skill_id].get("performance_profile", {})
            if not profile:
                profile = {
                    "avg_duration_seconds": 30,
                    "avg_token_cost": 2000,
                    "success_rate": 0.85,
                    "sample_count": 0
                }

            n = profile.get("sample_count", 0) + 1
            profile["avg_duration_seconds"] = (
                profile.get("avg_duration_seconds", 30) * (n - 1) + record["duration_seconds"]
            ) / n
            profile["avg_token_cost"] = (
                profile.get("avg_token_cost", 2000) * (n - 1) + record["token_cost"]
            ) / n
            success_val = 1 if record["outcome"] == "success" else 0
            profile["success_rate"] = (
                profile.get("success_rate", 0.85) * (n - 1) + success_val
            ) / n
            profile["sample_count"] = n

            self.registry["skill_registry"][skill_id]["performance_profile"] = profile

        # 写回文件
        atomic_write_json(registry_path, self.registry)

    def list_available(self) -> List[Dict]:
        """列出当前agent可用的所有skills及其信息"""
        available = []

        # 全局skills
        for skill_id in self.registry.get("global_skills", []):
            skill_meta = self.registry.get("skill_registry", {}).get(skill_id, {})
            available.append({
                "skill_id": skill_id,
                "source": "global",
                "description": skill_meta.get("description", ""),
                "estimated_cost": skill_meta.get("estimated_cost", "unknown")
            })

        # agent专属skills
        for skill_id in self.agent_skills:
            if skill_id in self.registry.get("skill_registry", {}):
                skill_meta = self.registry["skill_registry"][skill_id]
                available.append({
                    "skill_id": skill_id,
                    "source": "agent_specific",
                    "description": skill_meta.get("description", ""),
                    "estimated_cost": skill_meta.get("estimated_cost", "unknown")
                })

        return available

    def assign_skill(self, skill_id: str) -> bool:
        """用户手动为当前agent分配skill"""
        if skill_id not in self.registry.get("skill_registry", {}):
            return False
        if skill_id not in self.agent_skills:
            self.agent_skills.append(skill_id)
        return True

    def remove_skill(self, skill_id: str) -> bool:
        """移除agent的skill"""
        if skill_id in self.agent_skills:
            self.agent_skills.remove(skill_id)
            return True
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skill_manager.py <command> [args]")
        print("Commands: list, can_use, assign")
        sys.exit(1)
    cmd, *args = sys.argv[1:]
    if cmd == "list":
        task_dir = args[0]
        agent_id = args[1] if len(args) > 1 else None
        mgr = SkillManager(task_dir, agent_id)
        result = mgr.list_available()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "can_use":
        task_dir = args[0]
        agent_id = args[1]
        skill_id = args[2]
        mgr = SkillManager(task_dir, agent_id)
        allowed, reason = mgr.can_use(skill_id)
        print(json.dumps({"allowed": allowed, "reason": reason}, ensure_ascii=False))

    elif cmd == "assign":
        # 用户手动分配skill（写入manifest）
        agent_id = args[0]
        skill_id = args[1]
        mgr = SkillManager(None, agent_id)
        success = mgr.assign_skill(skill_id)
        if success:
            # 写回manifest
            base_dir = Path(__file__).parent.parent
            manifest_path = base_dir / ".claude" / "agents" / "manifest.json"
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if agent_id in manifest.get("agents", {}):
                if "skills" not in manifest["agents"][agent_id]:
                    manifest["agents"][agent_id]["skills"] = []
                if skill_id not in manifest["agents"][agent_id]["skills"]:
                    manifest["agents"][agent_id]["skills"].append(skill_id)
                    atomic_write_json(manifest_path, manifest)
            print(json.dumps({"status": "success", "agent_id": agent_id, "skill_id": skill_id}))
        else:
            print(json.dumps({"status": "error", "reason": f"未知skill: {skill_id}"}))

    else:
        print(f"[ERROR] 未知命令: {cmd} | 可用: list, can_use, assign")