"""PriorityQueue — 优先级队列模块。

实现优先级队列驱动的 Skill 执行调度（对齐 Haystack ComponentPriority）。
"""

import heapq
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional


class SkillPriority(IntEnum):
    """Skill 执行优先级（对齐 Haystack ComponentPriority）"""
    CRITICAL = 1     # 关键 Skill 优先执行
    READY = 2        # 就绪（依赖已满足）
    DEFER = 3        # 延迟（非关键，可稍后执行）
    DEFER_LAST = 4   # 最后执行（如归档类 Skill）
    BLOCKED = 5      # 阻塞（依赖未满足或被阻断）


@dataclass(order=True)
class PrioritizedSkill:
    """优先级队列中的 Skill 条目"""
    priority: SkillPriority
    skill_name: str = field(compare=False)
    context: Dict[str, Any] = field(compare=False, default_factory=dict)


class PrioritySkillQueue:
    """优先级队列（替代 V2 的固定拓扑层级）"""

    def __init__(self):
        self._queue: List[PrioritizedSkill] = []
        self._entries: Dict[str, PrioritizedSkill] = {}  # 去重

    def push(self, skill_name: str, priority: SkillPriority, context: Dict[str, Any] = None):
        """入队（自动去重，更新优先级）"""
        if skill_name in self._entries:
            # 更新优先级
            old = self._entries[skill_name]
            if priority != old.priority:
                self._queue.remove(old)
                entry = PrioritizedSkill(
                    priority=priority,
                    skill_name=skill_name,
                    context=context or {}
                )
                self._queue.append(entry)
                self._entries[skill_name] = entry
                heapq.heapify(self._queue)
        else:
            entry = PrioritizedSkill(
                priority=priority,
                skill_name=skill_name,
                context=context or {}
            )
            heapq.heappush(self._queue, entry)
            self._entries[skill_name] = entry

    def pop(self) -> Optional[PrioritizedSkill]:
        """出队（最高优先级优先）"""
        while self._queue:
            entry = heapq.heappop(self._queue)
            skill_name = entry.skill_name
            self._entries.pop(skill_name, None)
            return entry
        return None

    def peek(self) -> Optional[SkillPriority]:
        """查看最高优先级"""
        return self._queue[0].priority if self._queue else None

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return len(self._queue) == 0

    def __len__(self) -> int:
        return len(self._queue)

    def reprioritize(self, skill_name: str, new_priority: SkillPriority):
        """重新设置优先级（如依赖满足后从 BLOCKED 升级为 READY）"""
        if skill_name in self._entries:
            self.push(skill_name, new_priority, self._entries[skill_name].context)

    def contains(self, skill_name: str) -> bool:
        """检查 Skill 是否在队列中"""
        return skill_name in self._entries

    def get_priority(self, skill_name: str) -> Optional[SkillPriority]:
        """获取指定 Skill 的优先级"""
        if skill_name in self._entries:
            return self._entries[skill_name].priority
        return None

    def remove(self, skill_name: str) -> bool:
        """从队列中移除指定 Skill"""
        if skill_name in self._entries:
            entry = self._entries.pop(skill_name)
            self._queue.remove(entry)
            heapq.heapify(self._queue)
            return True
        return False

    def get_all_skills(self) -> List[str]:
        """获取队列中所有 Skill 名称"""
        return list(self._entries.keys())

    def clear(self):
        """清空队列"""
        self._queue.clear()
        self._entries.clear()

    def to_dict(self) -> List[Dict[str, Any]]:
        """序列化为字典列表"""
        return [
            {
                "skill_name": entry.skill_name,
                "priority": entry.priority.value,
                "context": entry.context
            }
            for entry in sorted(self._queue)
        ]

    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> 'PrioritySkillQueue':
        """从字典列表反序列化"""
        queue = cls()
        for item in data:
            queue.push(
                skill_name=item["skill_name"],
                priority=SkillPriority(item["priority"]),
                context=item.get("context", {})
            )
        return queue
