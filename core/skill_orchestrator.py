"""SkillOrchestrator — Skill 编排器模块。

集成 RetryPolicy、PriorityQueue、Heartbeat、EventSourcing 的完整编排器。
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .event_sourced_state import EventSourcedStateMachine, EventStore
from .heartbeat_checkpoint import HeartbeatCheckpoint, HeartbeatManager
from .priority_queue import PrioritySkillQueue, SkillPriority
from .retry_policy import RetryPolicy
from .saga_orchestrator import SagaOrchestrator


@dataclass
class SkillResult:
    """Skill 执行结果"""
    skill_name: str
    status: str  # "success", "failed", "timeout"
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 1
    duration_seconds: float = 0.0


class SkillOrchestrator:
    """
    Skill 编排器（集成所有稳定性机制）

    集成组件：
    1. RetryPolicy — Poisson 抖动重试
    2. PrioritySkillQueue — 优先级调度
    3. HeartbeatManager — 心跳检查点
    4. EventSourcedStateMachine — 事件溯源
    5. SagaOrchestrator — 补偿机制
    """

    def __init__(
        self,
        trace_id: str,
        artifacts_dir: Path = None,
        retry_policy: RetryPolicy = None,
    ):
        self.trace_id = trace_id
        self.artifacts_dir = artifacts_dir or Path("artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.retry_policy = retry_policy or RetryPolicy()
        self.priority_queue = PrioritySkillQueue()
        self.heartbeat_manager = HeartbeatManager(self.artifacts_dir / "heartbeats")

        # 事件溯源
        event_store = EventStore(self.artifacts_dir / "events.jsonl")
        self.state_machine = EventSourcedStateMachine(trace_id, event_store)

        # Saga 补偿
        self.saga: Optional[SagaOrchestrator] = None

        # 执行统计
        self.skill_results: Dict[str, SkillResult] = {}
        self.total_attempts = 0

    def enqueue_skill(
        self,
        skill_name: str,
        priority: SkillPriority = SkillPriority.READY,
        context: Dict[str, Any] = None,
    ):
        """将 Skill 加入优先级队列"""
        self.priority_queue.push(skill_name, priority, context or {})

    def execute_skill(
        self,
        skill_name: str,
        skill_func: Callable[[], Dict[str, Any]],
        timeout_seconds: float = 300.0,
        heartbeat_interval: float = 30.0,
        on_failure_compensate: Callable[[], Any] = None,
    ) -> SkillResult:
        """
        执行单个 Skill（带重试、心跳、事件溯源）

        Args:
            skill_name: Skill 名称
            skill_func: Skill 执行函数
            timeout_seconds: 超时时间
            heartbeat_interval: 心跳间隔
            on_failure_compensate: 失败补偿函数

        Returns:
            SkillResult: 执行结果
        """
        start_time = time.time()
        attempt = 0
        last_error_code = None
        last_error_message = None

        # 注册 Saga 补偿
        if self.saga and on_failure_compensate:
            self.saga.register_action(
                action_name=skill_name,
                compensation_func=on_failure_compensate,
            )

        # 获取心跳检查点
        checkpoint = self.heartbeat_manager.get_checkpoint(
            skill_name, heartbeat_interval
        )

        while attempt < self.retry_policy.maximum_attempts:
            attempt += 1
            self.total_attempts += 1

            try:
                # 报告心跳
                checkpoint.heartbeat({"phase": "executing", "attempt": attempt})

                # 执行 Skill
                result = skill_func()

                # 成功
                duration = time.time() - start_time
                skill_result = SkillResult(
                    skill_name=skill_name,
                    status="success",
                    outputs=result,
                    attempts=attempt,
                    duration_seconds=duration,
                )
                self.skill_results[skill_name] = skill_result

                # 记录到事件溯源
                self.state_machine.record_skill_result(skill_name, {
                    "status": "success",
                    "outputs": result,
                })

                checkpoint.heartbeat({"phase": "completed", "attempt": attempt})
                return skill_result

            except Exception as e:
                # 解析错误码
                error_code = getattr(e, "code", "EXE-101")
                error_message = str(e)
                last_error_code = error_code
                last_error_message = error_message

                # 判断是否可重试
                if not self.retry_policy.should_retry_error(error_code):
                    break

                # 计算退避时间
                if attempt < self.retry_policy.maximum_attempts:
                    delay = self.retry_policy.get_next_delay(attempt - 1)
                    time.sleep(delay)

        # 失败
        duration = time.time() - start_time
        skill_result = SkillResult(
            skill_name=skill_name,
            status="failed",
            error_code=last_error_code,
            error_message=last_error_message,
            attempts=attempt,
            duration_seconds=duration,
        )
        self.skill_results[skill_name] = skill_result

        # 记录失败到事件溯源
        self.state_machine.record_skill_result(skill_name, {
            "status": "failed",
            "error_code": last_error_code,
            "error_message": last_error_message,
        })

        return skill_result

    def execute_queue(
        self,
        skill_executor: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        max_skills: int = 100,
    ) -> List[SkillResult]:
        """
        执行优先级队列中的所有 Skill

        Args:
            skill_executor: Skill 执行器 (skill_name, context) -> result
            max_skills: 最大执行数量

        Returns:
            List[SkillResult]: 所有执行结果
        """
        results = []
        count = 0

        while not self.priority_queue.is_empty() and count < max_skills:
            entry = self.priority_queue.pop()
            if not entry:
                break

            count += 1
            skill_name = entry.skill_name
            context = entry.context

            # 进入阶段
            self.state_machine.enter_stage(skill_name, context)

            # 执行 Skill
            result = self.execute_skill(
                skill_name,
                lambda: skill_executor(skill_name, context),
            )
            results.append(result)

            # 失败则阻断
            if result.status == "failed":
                self.state_machine.block(f"Skill {skill_name} failed")
                break

        return results

    def start_saga(self, saga_id: str):
        """开始 Saga 编排"""
        self.saga = SagaOrchestrator(
            saga_id=saga_id,
            trace_id=self.trace_id,
            artifacts_dir=self.artifacts_dir / "sagas",
        )

    def complete_saga(self):
        """完成 Saga"""
        if self.saga:
            self.saga.mark_completed()

    def compensate_saga(self) -> Optional[Dict[str, Any]]:
        """执行 Saga 补偿"""
        if self.saga:
            return self.saga.compensate()
        return None

    def get_state(self) -> Dict[str, Any]:
        """获取编排器状态快照"""
        return {
            "trace_id": self.trace_id,
            "state_machine": self.state_machine.get_state(),
            "priority_queue": self.priority_queue.to_dict(),
            "skill_results": {
                name: {
                    "status": r.status,
                    "error_code": r.error_code,
                    "attempts": r.attempts,
                }
                for name, r in self.skill_results.items()
            },
            "total_attempts": self.total_attempts,
            "saga_state": self.saga.get_state() if self.saga else None,
        }
