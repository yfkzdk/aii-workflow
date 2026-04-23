"""SagaOrchestrator — Saga 补偿机制模块。

实现 Saga 补偿机制（对齐 Prefect on_rollback 钩子）。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class SagaState(Enum):
    """Saga 执行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


@dataclass
class CompensatingAction:
    """补偿动作"""
    action_id: str
    action_name: str
    compensation_func: Optional[Callable[[], Any]] = None
    compensation_command: Optional[str] = None
    executed_at: Optional[str] = None
    compensated_at: Optional[str] = None
    compensation_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "compensation_command": self.compensation_command,
            "executed_at": self.executed_at,
            "compensated_at": self.compensated_at,
            "compensation_error": self.compensation_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompensatingAction':
        return cls(
            action_id=data["action_id"],
            action_name=data["action_name"],
            compensation_command=data.get("compensation_command"),
            executed_at=data.get("executed_at"),
            compensated_at=data.get("compensated_at"),
            compensation_error=data.get("compensation_error"),
        )


@dataclass
class SagaExecution:
    """Saga 执行实例"""
    saga_id: str
    trace_id: str
    state: SagaState = SagaState.RUNNING
    actions: List[CompensatingAction] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    compensation_started_at: str = ""
    compensation_completed_at: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_id": self.saga_id,
            "trace_id": self.trace_id,
            "state": self.state.value,
            "actions": [a.to_dict() for a in self.actions],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "compensation_started_at": self.compensation_started_at,
            "compensation_completed_at": self.compensation_completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SagaExecution':
        return cls(
            saga_id=data["saga_id"],
            trace_id=data["trace_id"],
            state=SagaState(data["state"]),
            actions=[CompensatingAction.from_dict(a) for a in data.get("actions", [])],
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            compensation_started_at=data.get("compensation_started_at", ""),
            compensation_completed_at=data.get("compensation_completed_at", ""),
        )


class SagaOrchestrator:
    """
    Saga 编排器（对齐 Prefect on_rollback 钩子）

    核心原则：
    1. 每个动作都有对应的补偿动作
    2. 失败时按逆序执行补偿
    3. 补偿失败不阻断整体补偿流程
    """

    def __init__(self, saga_id: str, trace_id: str, artifacts_dir: Path = None):
        self.saga_id = saga_id
        self.trace_id = trace_id
        self.artifacts_dir = artifacts_dir or Path("artifacts/sagas")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.execution = SagaExecution(saga_id=saga_id, trace_id=trace_id)
        self._action_counter = 0

    def register_action(
        self,
        action_name: str,
        compensation_func: Callable[[], Any] = None,
        compensation_command: str = None,
    ) -> CompensatingAction:
        """注册动作及其补偿"""
        self._action_counter += 1
        action = CompensatingAction(
            action_id=f"{self.saga_id}-{self._action_counter}",
            action_name=action_name,
            compensation_func=compensation_func,
            compensation_command=compensation_command,
            executed_at=datetime.now().isoformat(),
        )
        self.execution.actions.append(action)
        self._persist()
        return action

    def mark_completed(self):
        """标记 Saga 完成"""
        self.execution.state = SagaState.COMPLETED
        self.execution.completed_at = datetime.now().isoformat()
        self._persist()

    def compensate(self) -> Dict[str, Any]:
        """
        执行补偿（逆序执行所有已执行动作的补偿）

        返回补偿结果摘要
        """
        if self.execution.state == SagaState.COMPLETED:
            return {"status": "skipped", "reason": "saga completed successfully"}

        self.execution.state = SagaState.COMPENSATING
        self.execution.compensation_started_at = datetime.now().isoformat()

        results = []
        # 逆序执行补偿
        for action in reversed(self.execution.actions):
            if not action.executed_at or action.compensated_at:
                continue

            try:
                # 优先执行补偿函数
                if action.compensation_func:
                    action.compensation_func()
                # 其次执行补偿命令
                elif action.compensation_command:
                    import subprocess
                    subprocess.run(
                        action.compensation_command,
                        shell=True,
                        check=True,
                        capture_output=True,
                    )

                action.compensated_at = datetime.now().isoformat()
                results.append({
                    "action_id": action.action_id,
                    "status": "success",
                })
            except Exception as e:
                action.compensation_error = str(e)
                results.append({
                    "action_id": action.action_id,
                    "status": "failed",
                    "error": str(e),
                })

        self.execution.state = SagaState.COMPENSATED
        self.execution.compensation_completed_at = datetime.now().isoformat()
        self._persist()

        return {
            "status": "completed",
            "actions_compensated": len([r for r in results if r["status"] == "success"]),
            "actions_failed": len([r for r in results if r["status"] == "failed"]),
            "details": results,
        }

    def _persist(self):
        """持久化 Saga 执行状态"""
        path = self.artifacts_dir / f"{self.saga_id}.json"
        path.write_text(
            json.dumps(self.execution.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @classmethod
    def recover(cls, saga_id: str, artifacts_dir: Path = None) -> Optional['SagaOrchestrator']:
        """从持久化状态恢复 Saga"""
        artifacts_dir = artifacts_dir or Path("artifacts/sagas")
        path = artifacts_dir / f"{saga_id}.json"

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            execution = SagaExecution.from_dict(data)

            orchestrator = cls(
                saga_id=execution.saga_id,
                trace_id=execution.trace_id,
                artifacts_dir=artifacts_dir,
            )
            orchestrator.execution = execution
            orchestrator._action_counter = len(execution.actions)
            return orchestrator
        except (json.JSONDecodeError, KeyError):
            return None

    def get_state(self) -> Dict[str, Any]:
        """获取 Saga 状态快照"""
        return self.execution.to_dict()
