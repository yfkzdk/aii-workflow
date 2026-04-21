"""Skill自动匹配引擎 — 根据任务特征自动选择最优skill"""

import json
import sys
from pathlib import Path
from typing import List, Dict


class SkillAutoMatcher:
    """自动匹配最优skill"""

    def __init__(self, skills_registry_path: str = None):
        self.registry_path = skills_registry_path or "config/skills.json"
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        path = Path(self.registry_path)
        if not path.exists():
            # 尝试相对路径
            base_dir = Path(__file__).parent.parent
            path = base_dir / "config" / "skills.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"skill_registry": {}, "global_skills": []}

    def match(self, agent_id: str, task_description: str, task_tags: List[str] = None,
              performance_weight: float = 0.5) -> List[Dict]:
        """
        为指定agent和任务自动匹配最优skills

        Args:
            agent_id: Agent标识
            task_description: 任务描述文本
            task_tags: 任务标签列表（可选）
            performance_weight: 性能权重（0-1），剩余权重给标签匹配

        Returns:
            按得分排序的skill列表
        """
        if task_tags is None:
            task_tags = self._extract_tags(task_description)

        candidates = []

        for skill_id, skill_meta in self.registry.get("skill_registry", {}).items():
            # 1. 检查agent是否适用
            if agent_id not in skill_meta.get("applicable_agents", []):
                continue

            # 2. 计算标签匹配得分
            tag_score = self._tag_similarity(task_tags, skill_meta.get("match_tags", []))

            # 3. 计算性能得分
            perf = skill_meta.get("performance_profile", {})
            perf_score = self._calculate_perf_score(perf)

            # 4. 综合得分
            total_score = tag_score * (1 - performance_weight) + perf_score * performance_weight

            # 5. 生成解释
            reason = self._explain(skill_id, tag_score, perf_score, task_tags, skill_meta.get("match_tags", []))

            candidates.append({
                "skill_id": skill_id,
                "score": round(total_score, 3),
                "tag_score": round(tag_score, 3),
                "perf_score": round(perf_score, 3),
                "reason": reason,
                "source": "auto_match",
                "estimated_duration": perf.get("avg_duration_seconds", 0),
                "estimated_cost": skill_meta.get("estimated_cost", "unknown")
            })

        # 按得分排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    def match_for_proposal(self, agent_id: str, proposal_id: str, features: dict) -> List[Dict]:
        """为特定方案匹配skills"""
        # 从features中提取领域标签
        task_tags = features.get("domain_tags", [])

        # 方案复杂度影响权重
        complexity = features.get("complexity_score", 1.0)
        perf_weight = min(0.7, 0.3 + complexity * 0.1)  # 复杂度越高，性能权重越重要

        return self.match(agent_id, "", task_tags, perf_weight)

    def _extract_tags(self, text: str) -> List[str]:
        """从文本中提取标签"""
        text_lower = text.lower()
        tag_keywords = {
            "frontend": ["前端", "ui", "界面", "页面", "html", "css", "javascript", "web"],
            "backend": ["后端", "api", "服务端", "server", "数据库", "database"],
            "security": ["安全", "加密", "认证", "auth", "登录", "权限", "漏洞"],
            "game": ["游戏", "棋", "对战", "玩家", "ai"],
            "network": ["网络", "联机", "在线", "websocket", "http", "tcp"],
            "code-quality": ["优化", "重构", "简化", "clean", "refactor"],
            "api": ["api", "接口", "sdk", "集成"]
        }

        extracted = []
        for tag, keywords in tag_keywords.items():
            if any(kw in text_lower for kw in keywords):
                extracted.append(tag)

        return extracted

    def _tag_similarity(self, task_tags: List[str], skill_tags: List[str]) -> float:
        """Jaccard相似度"""
        if not task_tags or not skill_tags:
            return 0.0
        t, s = set(task_tags), set(skill_tags)
        intersection = len(t & s)
        union = len(t | s)
        return intersection / union if union > 0 else 0.0

    def _calculate_perf_score(self, perf: dict) -> float:
        """计算性能得分"""
        if not perf:
            return 0.5  # 默认中等分数

        success_rate = perf.get("success_rate", 0.85)
        avg_duration = perf.get("avg_duration_seconds", 30)

        # 速度归一化：30秒为基准，越快越好
        speed_score = 1 / (1 + avg_duration / 60)

        return success_rate * 0.6 + speed_score * 0.4

    def _explain(self, skill_id: str, tag_score: float, perf_score: float,
                 task_tags: List[str], skill_tags: List[str]) -> str:
        """生成匹配解释"""
        reasons = []

        if tag_score > 0.3:
            matched = set(task_tags) & set(skill_tags)
            reasons.append(f"标签匹配({', '.join(matched)})")
        if perf_score > 0.7:
            reasons.append("历史性能优秀")
        elif perf_score > 0.5:
            reasons.append("历史性能良好")

        return f"{skill_id}: {'; '.join(reasons) if reasons else '通用匹配'}"

    def get_skill_info(self, skill_id: str) -> dict:
        """获取单个skill的详细信息"""
        return self.registry.get("skill_registry", {}).get(skill_id, {})

    def list_applicable_skills(self, agent_id: str) -> List[str]:
        """列出agent可用的所有skills"""
        applicable = []
        for skill_id, skill_meta in self.registry.get("skill_registry", {}).items():
            if agent_id in skill_meta.get("applicable_agents", []):
                applicable.append(skill_id)
        return applicable


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skill_auto_matcher.py <command> [args]")
        print("Commands: match, list, info")
        sys.exit(1)
    cmd, *args = sys.argv[1:]
    if cmd == "match":
        # python skill_auto_matcher.py match <agent_id> <task_description>
        agent_id = args[0]
        task_desc = " ".join(args[1:]) if len(args) > 1 else ""

        matcher = SkillAutoMatcher()
        results = matcher.match(agent_id, task_desc)

        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif cmd == "list":
        # python skill_auto_matcher.py list <agent_id>
        agent_id = args[0]
        matcher = SkillAutoMatcher()
        skills = matcher.list_applicable_skills(agent_id)

        print(json.dumps({"agent_id": agent_id, "applicable_skills": skills}, ensure_ascii=False, indent=2))

    elif cmd == "info":
        # python skill_auto_matcher.py info <skill_id>
        skill_id = args[0]
        matcher = SkillAutoMatcher()
        info = matcher.get_skill_info(skill_id)

        print(json.dumps(info, ensure_ascii=False, indent=2))

    else:
        print(f"[ERROR] 未知命令: {cmd} | 可用: match, list, info")