"""EventSourcedState — 事件溯源状态机模块。

实现事件溯源状态机（对齐 Temporal 的确定性重放模型）。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class EventType(Enum):
    """状态机事件类型"""
    STAGE_ENTERED = "stage_entered"
    STAGE_COMPLETED = "stage_completed"
    SKILL_EXECUTION_STARTED = "skill_execution_started"
    SKILL_EXECUTION_COMPLETED = "skill_execution_completed"
    SKILL_EXECUTION_FAILED = "skill_execution_failed"
    QUALITY_GATE_EVALUATED = "quality_gate_evaluated"
    PIPELINE_BLOCKED = "pipeline_blocked"
    PIPELINE_UNBLOCKED = "pipeline_unblocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_COMPLETED = "approval_completed"
    COMPENSATION_STARTED = "compensation_started"
    COMPENSATION_COMPLETED = "compensation_completed"


@dataclass
class StateEvent:
    """状态事件（事件溯源的基本单元）"""
    event_id: int
    event_type: EventType
    timestamp: str
    trace_id: str
    payload: Dict[str, Any]
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "payload": self.payload,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateEvent':
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            trace_id=data["trace_id"],
            payload=data["payload"],
            idempotency_key=data.get("idempotency_key"),
        )


class EventStore:
    """事件存储（追加写入，支持确定性重放）"""

    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._next_event_id = self._get_last_event_id() + 1
        self._applied_events: Set[str] = set()

    def append(self, event: StateEvent) -> StateEvent:
        """追加事件（原子写入）"""
        event.event_id = self._next_event_id
        self._next_event_id += 1

        # 幂等性检查
        if event.idempotency_key and event.idempotency_key in self._applied_events:
            return event

        # 追加写入
        with open(self.store_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

        if event.idempotency_key:
            self._applied_events.add(event.idempotency_key)

        return event

    def read_all(self) -> List[StateEvent]:
        """读取所有事件（用于确定性重放）"""
        events = []
        if not self.store_path.exists():
            return events

        for line in self.store_path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    events.append(StateEvent.from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue

        return sorted(events, key=lambda e: e.event_id)

    def _get_last_event_id(self) -> int:
        """获取最后一个事件 ID"""
        if not self.store_path.exists():
            return 0
        events = self.read_all()
        return events[-1].event_id if events else 0


class EventSourcedStateMachine:
    """
    事件溯源状态机（对齐 Temporal 的确定性重放模型）

    核心原则：
    1. 状态 = f(事件历史) — 任何时刻的状态都可以从事件历史重放得出
    2. 事件不可变 — 只追加，不修改、不删除
    3. 确定性重放 — 相同事件序列 → 相同状态
    """

    def __init__(self, trace_id: str, event_store: EventStore):
        self.trace_id = trace_id
        self.event_store = event_store

        # 当前状态（由事件驱动，非直接修改）
        self.current_stage: str = "init"
        self.blocked_reason: Optional[str] = None
        self.stage_context: Dict[str, Any] = {}
        self.skill_results: Dict[str, Dict[str, Any]] = {}
        self.quality_reports: Dict[str, Dict[str, Any]] = {}

        # 从事件历史重建状态
        self._replay_from_events()

    def _replay_from_events(self):
        """从事件历史确定性重放（崩溃恢复的核心）"""
        events = self.event_store.read_all()
        for event in events:
            self._apply_event(event)

    def _apply_event(self, event: StateEvent):
        """应用单个事件（纯函数，无副作用）"""
        if event.event_type == EventType.STAGE_ENTERED:
            self.current_stage = event.payload.get("stage", "init")
            self.stage_context = event.payload.get("context", {})

        elif event.event_type == EventType.STAGE_COMPLETED:
            self.stage_context = event.payload.get("context", {})

        elif event.event_type == EventType.SKILL_EXECUTION_COMPLETED:
            skill_name = event.payload.get("skill_name")
            if skill_name:
                self.skill_results[skill_name] = event.payload.get("result", {})

        elif event.event_type == EventType.SKILL_EXECUTION_FAILED:
            skill_name = event.payload.get("skill_name")
            if skill_name:
                self.skill_results[skill_name] = {
                    "status": "failed",
                    "error_code": event.payload.get("error_code"),
                    "error_message": event.payload.get("error_message"),
                }

        elif event.event_type == EventType.QUALITY_GATE_EVALUATED:
            stage = event.payload.get("stage")
            if stage:
                self.quality_reports[stage] = {
                    "passed": event.payload.get("passed", False),
                    "errors": event.payload.get("errors", []),
                    "action": event.payload.get("action", "proceed"),
                }

        elif event.event_type == EventType.PIPELINE_BLOCKED:
            self.blocked_reason = event.payload.get("reason", "")

        elif event.event_type == EventType.PIPELINE_UNBLOCKED:
            self.blocked_reason = None
            self.current_stage = event.payload.get("resume_stage", self.current_stage)

        elif event.event_type == EventType.APPROVAL_COMPLETED:
            if event.payload.get("approved", False):
                self.blocked_reason = None

    # === 状态变更方法（通过事件驱动，不直接修改状态）===

    def enter_stage(self, stage: str, context: Dict[str, Any] = None):
        """进入阶段（通过事件驱动）"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.STAGE_ENTERED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"stage": stage, "context": context or {}},
            idempotency_key=f"enter_{stage}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def complete_stage(self, context: Dict[str, Any] = None):
        """完成当前阶段"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.STAGE_COMPLETED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"stage": self.current_stage, "context": context or {}},
        )
        self.event_store.append(event)
        self._apply_event(event)

    def record_skill_result(self, skill_name: str, result: Dict[str, Any]):
        """记录 Skill 执行结果"""
        is_success = result.get("status") == "success"
        event_type = (
            EventType.SKILL_EXECUTION_COMPLETED
            if is_success
            else EventType.SKILL_EXECUTION_FAILED
        )
        event = StateEvent(
            event_id=0,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={
                "skill_name": skill_name,
                "result": result if is_success else None,
                "error_code": result.get("error_code") if not is_success else None,
                "error_message": result.get("error_message") if not is_success else None,
            },
            idempotency_key=f"skill_{skill_name}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def record_quality_gate(self, stage: str, passed: bool, errors: List[str] = None,
                           action: str = "proceed"):
        """记录质量门评估结果"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.QUALITY_GATE_EVALUATED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={
                "stage": stage,
                "passed": passed,
                "errors": errors or [],
                "action": action,
            },
        )
        self.event_store.append(event)
        self._apply_event(event)

    def block(self, reason: str):
        """阻断流水线"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.PIPELINE_BLOCKED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"reason": reason, "stage": self.current_stage},
            idempotency_key=f"block_{self.current_stage}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def unblock(self, resume_stage: str = None, reason: str = ""):
        """解除阻断"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.PIPELINE_UNBLOCKED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={
                "resume_stage": resume_stage or self.current_stage,
                "reason": reason
            },
            idempotency_key=f"unblock_{resume_stage or self.current_stage}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态快照"""
        return {
            "current_stage": self.current_stage,
            "blocked_reason": self.blocked_reason,
            "stage_context": self.stage_context,
            "skill_results": self.skill_results,
            "quality_reports": self.quality_reports,
        }

    @classmethod
    def recover(cls, trace_id: str, event_store_path: Path) -> 'EventSourcedStateMachine':
        """从事件存储恢复状态机（崩溃恢复入口）"""
        event_store = EventStore(event_store_path)
        return cls(trace_id=trace_id, event_store=event_store)
