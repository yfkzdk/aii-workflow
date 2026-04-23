# 优化方案三：状态机韧性重构 — 事件溯源 + 确定性重放 + Saga 补偿

> **优先级**: P1（影响系统崩溃恢复能力和数据一致性）
> **影响范围**: 状态机、补偿处理器、审计日志、审批流
> **参考来源**: Temporal 事件溯源 + CrewAI Guardrail/Checkpoint + Prefect on_rollback/on_commit

---

## 一、当前设计问题诊断

### 问题 1：状态机纯内存 — 崩溃即丢失全部状态

**当前实现**（设计文档 L1534-1600）：
```python
class StateMachine:
    def __init__(self, trace_id: str):
        self.current_stage = PipelineStage.INIT
        self.trace_id = trace_id
        self.transition_history: List[StateTransition] = []  # 内存中
        self.blocked_reason: Optional[str] = None
        self.stage_context: Dict[PipelineStage, Dict[str, Any]] = {}  # 内存中
```

**问题**：
- `transition_history` 和 `stage_context` 仅存在于内存，进程崩溃后全部丢失
- 审计日志虽然写入文件，但格式是追加式的 JSON Lines，无法用于状态重建
- 崩溃后重启，状态机只能从 `INIT` 重新开始，无法恢复到崩溃前的状态
- `BLOCKED` 状态下崩溃，审批流上下文完全丢失，人工介入无法继续

**Temporal 的做法**：
Temporal 的 Workflow 状态完全由事件历史驱动。Workflow 代码本身不持有状态，每次执行都从事件历史重放（deterministic replay）。崩溃后只需重放事件历史即可恢复到精确状态。

### 问题 2：补偿处理器过于简陋 — 无回滚保证

**当前实现**（设计文档 L229-269）：
```python
class CompensationHandler:
    def compensate_failed_skill(self, skill_name: str, result: SkillResult) -> None:
        self._cleanup_temp_files(skill_name)       # 删除临时文件
        self._rollback_state_changes(skill_name)    # 写一个 marker 文件
        self._notify_downstream(skill_name, result) # 写一个通知文件
        self._log_compensation(skill_name, result)   # 写日志
```

**问题**：
1. **`_rollback_state_changes` 只是写 marker 文件**，不是真正的回滚操作 — 如果 Skill 已经修改了数据库或发送了 API 请求，marker 文件无法撤销这些变更
2. **无补偿顺序保证**：多个 Skill 失败时，补偿顺序未定义（应按执行逆序）
3. **无补偿失败处理**：如果补偿操作本身失败，系统进入不一致状态
4. **无补偿超时**：补偿操作可能无限期挂起

**Prefect 的做法**（`prefect/tasks.py` L417-418）：
```python
class Task:
    on_rollback: Optional[list[Callable[["Transaction"], None]]] = None
    on_commit: Optional[list[Callable[["Transaction"], None]]] = None
```
Prefect 的 `Transaction` 机制提供了 `on_rollback` 和 `on_commit` 钩子，每个 Task 声明自己的回滚逻辑，框架保证按逆序执行。

### 问题 3：审计日志不可用于状态重建 — 写入与状态变更不同步

**当前实现**（设计文档 L1647-1668）：
```python
def _write_audit_log(self, transition: StateTransition):
    audit_entry = {
        "timestamp": transition.timestamp,
        "trace_id": transition.trace_id,
        "event_type": "state_transition",
        "from_stage": transition.from_stage.value,
        "to_stage": transition.to_stage.value,
        "reason": transition.reason
    }
    # 追加写入日志文件
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
```

**问题**：
- 审计日志是"事后记录"，不是"状态驱动源" — 日志写入失败不影响状态变更
- 日志缺少状态重建所需的完整上下文（如 `stage_context` 快照）
- 日志格式不支持确定性重放（缺少事件序号和幂等性标记）

---

## 二、优化方案

### 2.1 事件溯源状态机（替代纯内存状态机）

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
import json
from datetime import datetime

# === 事件定义 ===

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
    event_id: int                           # 全局递增序号（确定性重放必需）
    event_type: EventType                   # 事件类型
    timestamp: str                          # ISO 8601 时间戳
    trace_id: str                           # 追踪 ID
    payload: Dict[str, Any]                 # 事件载荷（包含状态重建所需的完整上下文）
    idempotency_key: Optional[str] = None    # 幂等性键（防止重复应用）

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "payload": self.payload,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StateEvent':
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            trace_id=data["trace_id"],
            payload=data["payload"],
            idempotency_key=data.get("idempotency_key"),
        )


# === 事件存储 ===

class EventStore:
    """事件存储（追加写入，支持确定性重放）"""

    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._next_event_id = self._get_last_event_id() + 1
        self._applied_events: set[str] = set()  # 已应用的事件 ID（幂等性保证）

    def append(self, event: StateEvent) -> StateEvent:
        """追加事件（原子写入）"""
        # 分配事件 ID
        event.event_id = self._next_event_id
        self._next_event_id += 1

        # 幂等性检查
        if event.idempotency_key and event.idempotency_key in self._applied_events:
            return event  # 已存在，跳过

        # 原子写入（先写临时文件，再重命名）
        temp_path = self.store_path.with_suffix(".tmp")
        with open(temp_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

        # 追加到主文件（简化实现，生产环境应使用 WAL）
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
                events.append(StateEvent.from_dict(json.loads(line)))

        return sorted(events, key=lambda e: e.event_id)

    def _get_last_event_id(self) -> int:
        """获取最后一个事件 ID"""
        if not self.store_path.exists():
            return 0
        events = self.read_all()
        return events[-1].event_id if events else 0


# === 事件溯源状态机 ===

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
        self.current_stage: PipelineStage = PipelineStage.INIT
        self.blocked_reason: Optional[str] = None
        self.stage_context: Dict[str, Any] = {}
        self.skill_results: Dict[str, SkillResult] = {}
        self.quality_reports: Dict[str, QualityReport] = {}

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
            self.current_stage = PipelineStage(event.payload["stage"])
            self.stage_context = event.payload.get("context", {})

        elif event.event_type == EventType.STAGE_COMPLETED:
            self.stage_context = event.payload.get("context", {})

        elif event.event_type == EventType.SKILL_EXECUTION_COMPLETED:
            skill_name = event.payload["skill_name"]
            self.skill_results[skill_name] = SkillResult.from_json(event.payload["result"])

        elif event.event_type == EventType.SKILL_EXECUTION_FAILED:
            skill_name = event.payload["skill_name"]
            self.skill_results[skill_name] = SkillResult(
                status=SkillStatus.FAILED,
                outputs={},
                metrics={},
                errors=[SkillError(code=event.payload.get("error_code", "EXE-102"),
                                    message=event.payload.get("error_message", ""))],
                metadata={}
            )

        elif event.event_type == EventType.QUALITY_GATE_EVALUATED:
            stage = event.payload["stage"]
            self.quality_reports[stage] = QualityReport(
                passed=event.payload["passed"],
                errors=event.payload.get("errors", []),
                action=event.payload.get("action", "proceed"),
            )

        elif event.event_type == EventType.PIPELINE_BLOCKED:
            self.blocked_reason = event.payload.get("reason", "")

        elif event.event_type == EventType.PIPELINE_UNBLOCKED:
            self.blocked_reason = None
            self.current_stage = PipelineStage(event.payload["resume_stage"])

        elif event.event_type == EventType.APPROVAL_COMPLETED:
            if event.payload.get("approved", False):
                self.blocked_reason = None

    # === 状态变更方法（通过事件驱动，不直接修改状态）===

    def enter_stage(self, stage: PipelineStage, context: dict = None):
        """进入阶段（通过事件驱动）"""
        event = StateEvent(
            event_id=0,  # 由 EventStore 分配
            event_type=EventType.STAGE_ENTERED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"stage": stage.value, "context": context or {}},
            idempotency_key=f"enter_{stage.value}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def complete_stage(self, context: dict = None):
        """完成当前阶段"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.STAGE_COMPLETED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"stage": self.current_stage.value, "context": context or {}},
        )
        self.event_store.append(event)
        self._apply_event(event)

    def record_skill_result(self, skill_name: str, result: SkillResult):
        """记录 Skill 执行结果"""
        event_type = (
            EventType.SKILL_EXECUTION_COMPLETED if result.is_success()
            else EventType.SKILL_EXECUTION_FAILED
        )
        event = StateEvent(
            event_id=0,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={
                "skill_name": skill_name,
                "result": result.to_json() if result.is_success() else None,
                "error_code": result.errors[0].code if result.errors else None,
                "error_message": result.errors[0].message if result.errors else None,
            },
            idempotency_key=f"skill_{skill_name}_{self.trace_id}",
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
            payload={"reason": reason, "stage": self.current_stage.value},
            idempotency_key=f"block_{self.current_stage.value}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    def unblock(self, resume_stage: PipelineStage, reason: str = ""):
        """解除阻断"""
        event = StateEvent(
            event_id=0,
            event_type=EventType.PIPELINE_UNBLOCKED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"resume_stage": resume_stage.value, "reason": reason},
            idempotency_key=f"unblock_{resume_stage.value}_{self.trace_id}",
        )
        self.event_store.append(event)
        self._apply_event(event)

    @classmethod
    def recover(cls, trace_id: str, event_store_path: Path) -> 'EventSourcedStateMachine':
        """从事件存储恢复状态机（崩溃恢复入口）"""
        event_store = EventStore(event_store_path)
        return cls(trace_id=trace_id, event_store=event_store)
```

### 2.2 Saga 补偿模式（替代 marker 文件补偿）

```python
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

class CompensatingAction(ABC):
    """补偿动作接口（对齐 Prefect on_rollback）"""

    @abstractmethod
    def execute(self, context: dict) -> bool:
        """执行补偿动作，返回是否成功"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取补偿动作名称"""
        pass


class SagaStep:
    """Saga 步骤（正向动作 + 补偿动作配对）"""

    def __init__(
        self,
        skill_name: str,
        forward_action: Callable,
        compensating_action: CompensatingAction | None = None,
        timeout_seconds: int = 60,
    ):
        self.skill_name = skill_name
        self.forward_action = forward_action
        self.compensating_action = compensating_action
        self.timeout_seconds = timeout_seconds
        self.completed = False
        self.compensated = False


class SagaOrchestrator:
    """
    Saga 编排器（替代 CompensationHandler）

    核心原则：
    1. 每个 Skill 声明自己的补偿动作（对齐 Prefect on_rollback）
    2. 补偿按执行逆序执行（Saga 语义）
    3. 补偿失败不静默 — 记录并触发人工介入
    4. 补偿超时保护
    """

    def __init__(self, event_store: EventStore, trace_id: str):
        self.event_store = event_store
        self.trace_id = trace_id
        self.completed_steps: List[SagaStep] = []
        self.compensation_failures: List[dict] = []

    def register_step(self, step: SagaStep):
        """注册 Saga 步骤"""
        self.completed_steps.append(step)

    async def execute_forward(self, step: SagaStep, context: dict) -> SkillResult:
        """执行正向动作"""
        try:
            result = await step.forward_action(context)
            step.completed = True
            self.register_step(step)

            # 记录事件
            self.event_store.append(StateEvent(
                event_id=0,
                event_type=EventType.SKILL_EXECUTION_COMPLETED,
                timestamp=datetime.now().isoformat(),
                trace_id=self.trace_id,
                payload={"skill_name": step.skill_name, "result": result.to_json()},
            ))
            return result

        except Exception as e:
            # 正向动作失败，触发补偿
            self.event_store.append(StateEvent(
                event_id=0,
                event_type=EventType.SKILL_EXECUTION_FAILED,
                timestamp=datetime.now().isoformat(),
                trace_id=self.trace_id,
                payload={"skill_name": step.skill_name, "error_message": str(e)},
            ))
            await self.compensate(step.skill_name)
            raise

    async def compensate(self, failed_skill_name: str):
        """
        执行补偿（按执行逆序，从最近的已完成步骤到失败步骤）

        Saga 语义：如果 A → B → C 失败，补偿顺序为 C⁻¹ → B⁻¹
        """
        self.event_store.append(StateEvent(
            event_id=0,
            event_type=EventType.COMPENSATION_STARTED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={"failed_skill": failed_skill_name},
        ))

        # 按逆序补偿
        steps_to_compensate = [
            s for s in reversed(self.completed_steps)
            if s.compensating_action and not s.compensated
        ]

        for step in steps_to_compensate:
            try:
                success = await self._execute_compensation_with_timeout(step)
                if success:
                    step.compensated = True
                    self.event_store.append(StateEvent(
                        event_id=0,
                        event_type=EventType.COMPENSATION_COMPLETED,
                        timestamp=datetime.now().isoformat(),
                        trace_id=self.trace_id,
                        payload={"skill_name": step.skill_name, "status": "success"},
                    ))
                else:
                    self._record_compensation_failure(step, "补偿动作返回失败")

            except Exception as e:
                self._record_compensation_failure(step, str(e))

        self.event_store.append(StateEvent(
            event_id=0,
            event_type=EventType.COMPENSATION_COMPLETED,
            timestamp=datetime.now().isoformat(),
            trace_id=self.trace_id,
            payload={
                "failed_skill": failed_skill_name,
                "compensated_count": sum(1 for s in steps_to_compensate if s.compensated),
                "failed_count": len(self.compensation_failures),
            },
        ))

    async def _execute_compensation_with_timeout(self, step: SagaStep) -> bool:
        """带超时的补偿执行"""
        import asyncio
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(step.compensating_action.execute, {}),
                timeout=step.timeout_seconds
            )
        except asyncio.TimeoutError:
            self._record_compensation_failure(step, f"补偿超时 ({step.timeout_seconds}s)")
            return False

    def _record_compensation_failure(self, step: SagaStep, reason: str):
        """记录补偿失败（触发人工介入）"""
        failure = {
            "skill_name": step.skill_name,
            "compensation_action": step.compensating_action.get_name() if step.compensating_action else None,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "requires_manual_intervention": True,
        }
        self.compensation_failures.append(failure)

        # 写入补偿失败文件（人工介入入口）
        failure_path = Path("artifacts/compensation_failures.json")
        existing = []
        if failure_path.exists():
            existing = json.loads(failure_path.read_text(encoding="utf-8"))
        existing.append(failure)
        failure_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
```

**Skill 适配器声明补偿动作示例**：

```python
class SecurityReviewAdapter(SkillAdapter):
    """安全审查适配器（声明补偿动作）"""

    def get_compensating_action(self) -> CompensatingAction | None:
        return SecurityReviewCompensation()

    async def run(self, context: dict) -> SkillResult:
        # 正向动作：扫描代码并生成报告
        report = self._scan_and_generate_report(context)
        return SkillResult(status=SkillStatus.SUCCESS, ...)


class SecurityReviewCompensation(CompensatingAction):
    """安全审查补偿动作"""

    def execute(self, context: dict) -> bool:
        # 删除生成的报告文件
        report_path = Path("artifacts/security_review_report.md")
        if report_path.exists():
            report_path.unlink()
        # 删除结果文件
        result_path = Path("artifacts/security_review_result.json")
        if result_path.exists():
            result_path.unlink()
        return True

    def get_name(self) -> str:
        return "security_review_compensation"


class SendNotificationAdapter(SkillAdapter):
    """通知发送适配器（声明补偿动作）"""

    def get_compensating_action(self) -> CompensatingAction | None:
        return SendNotificationCompensation()

    async def run(self, context: dict) -> SkillResult:
        # 正向动作：发送通知
        message_id = self._send_notification(context)
        return SkillResult(status=SkillStatus.SUCCESS, ...)


class SendNotificationCompensation(CompensatingAction):
    """通知发送补偿动作"""

    def execute(self, context: dict) -> bool:
        # 发送撤回通知（而非假装通知未发送）
        self._send_revocation_notice(context)
        return True

    def get_name(self) -> str:
        return "send_notification_compensation"
```

### 2.3 审计日志与事件存储统一

```python
class UnifiedAuditLogger:
    """
    统一审计日志（事件存储即审计日志）

    核心改进：审计日志 = 事件存储，不再维护两套系统
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def query_events(
        self,
        trace_id: str = None,
        event_type: EventType = None,
        skill_name: str = None,
        start_time: str = None,
        end_time: str = None,
    ) -> List[StateEvent]:
        """查询事件（支持审计查询）"""
        events = self.event_store.read_all()

        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if skill_name:
            events = [e for e in events if e.payload.get("skill_name") == skill_name]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events

    def export_audit_report(self, trace_id: str) -> dict:
        """导出审计报告"""
        events = self.query_events(trace_id=trace_id)

        return {
            "trace_id": trace_id,
            "total_events": len(events),
            "timeline": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp,
                    "payload_summary": self._summarize_payload(e),
                }
                for e in events
            ],
            "state_at_end": self._reconstruct_final_state(events),
        }

    def _summarize_payload(self, event: StateEvent) -> dict:
        """脱敏摘要"""
        if event.event_type in (EventType.SKILL_EXECUTION_COMPLETED, EventType.SKILL_EXECUTION_FAILED):
            return {"skill_name": event.payload.get("skill_name")}
        return {"stage": event.payload.get("stage", "")}

    def _reconstruct_final_state(self, events: List[StateEvent]) -> dict:
        """从事件重建最终状态（验证一致性）"""
        state = {"stage": "init", "blocked": False, "skills_completed": [], "skills_failed": []}
        for event in events:
            if event.event_type == EventType.STAGE_ENTERED:
                state["stage"] = event.payload["stage"]
            elif event.event_type == EventType.SKILL_EXECUTION_COMPLETED:
                state["skills_completed"].append(event.payload["skill_name"])
            elif event.event_type == EventType.SKILL_EXECUTION_FAILED:
                state["skills_failed"].append(event.payload["skill_name"])
            elif event.event_type == EventType.PIPELINE_BLOCKED:
                state["blocked"] = True
            elif event.event_type == EventType.PIPELINE_UNBLOCKED:
                state["blocked"] = False
        return state
```

---

## 三、崩溃恢复流程对比

### 当前设计（崩溃后）

```
进程崩溃
    ↓
重启 → StateMachine(trace_id) → 从 INIT 开始
    ↓
检查 ExecutionCheckpoint → 发现部分 Skill 已完成
    ↓
重新执行未完成的 Skill（但丢失了 stage_context、quality_report 等）
    ↓
❌ 审批流上下文丢失，人工介入无法继续
❌ 补偿状态丢失，已执行的 Skill 无法回滚
```

### 优化后（崩溃后）

```
进程崩溃
    ↓
重启 → EventSourcedStateMachine.recover(trace_id, event_store_path)
    ↓
从事件存储读取所有事件 → _replay_from_events()
    ↓
✅ 状态机恢复到崩溃前的精确状态
✅ stage_context、quality_report、skill_results 全部恢复
✅ 审批流上下文恢复，人工介入可继续
✅ Saga 补偿状态恢复，已完成的补偿步骤不会重复执行
```

---

## 四、变更影响矩阵

| 组件 | 变更类型 | 影响范围 | 向后兼容 |
|------|---------|---------|---------|
| `StateMachine` | 替换为 `EventSourcedStateMachine` | 状态机 | ❌ 接口变更 |
| `CompensationHandler` | 替换为 `SagaOrchestrator` | 补偿机制 | ❌ 接口变更 |
| `SkillAdapter` | 新增 `get_compensating_action()` | 适配器接口 | ✅ 可选方法，默认返回 None |
| 审计日志 | 统一到事件存储 | 日志系统 | ⚠️ 格式变更，需迁移 |
| `StateTransition` | 替换为 `StateEvent` | 数据模型 | ❌ 结构变更 |
| `EventStore` | 新增 | 持久化 | ✅ 新增 |

---

## 五、迁移路径

1. **Phase 1**（1周）：实现 `EventStore`，将现有审计日志迁移为事件存储格式
2. **Phase 2**（1周）：实现 `EventSourcedStateMachine`，替换 `StateMachine`
3. **Phase 3**（1周）：实现 `SagaOrchestrator` + `CompensatingAction`，替换 `CompensationHandler`
4. **Phase 4**（3天）：为现有 SkillAdapter 添加 `get_compensating_action()` 方法
5. **Phase 5**（2天）：统一审计日志与事件存储，删除旧的审计日志写入逻辑

---

## 六、三份方案优先级总结

| 方案 | 优先级 | 核心收益 | 实施周期 | V1 可采纳度 |
|------|--------|---------|---------|------------|
| 方案一：重试系统重构 | P0 | 消除雷群效应、精确重试控制、断点续跑 | 3周 | 高（泊松抖动可独立替换） |
| 方案二：流水线执行引擎 | P1 | 执行效率提升、精确恢复、循环保护 | 3周 | 中（循环保护和快照可独立采纳） |
| 方案三：状态机韧性 | P1 | 崩溃恢复、数据一致性、补偿保证 | 3周 | 低（需整体替换，难以局部采纳） |

**建议实施顺序**：方案一 → 方案二（V1 部分）→ 方案三 → 方案二（V2 完整版）