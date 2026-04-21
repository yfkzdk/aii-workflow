"""SafeState -- 有界状态模型，支持快照/回滚和确认门限流。

核心保证：
- current_step_index 永远在 [0, len(pipeline)-1] 范围内
- 确认门回退次数有上限（默认 4 次），防止无限循环
- 快照/回滚机制支持安全撤销
- v2 兼容：可读写现有 state.json 格式
"""

import json
import copy
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

ENHANCED_PIPELINE = [
    "input_collecting", "requirement_optimizing", "confirmation",
    "planning", "prompt_optimizing", "executing",
    "verifying", "archiving", "completed"
]

TERMINAL_STATES = {"completed", "cancelled"}


@dataclass
class _Snapshot:
    data: Dict[str, Any]
    timestamp: str
    label: str


@dataclass
class SafeState:
    """管线状态，步进索引永远有界。

    面试话术锚点：
    - _enforce_invariants() 保证索引永不出界
    - confirm_action() 有回退上限，防无限循环
    - snapshot()/rollback() 提供安全撤销能力
    """

    task_id: str
    pipeline: List[str] = field(default_factory=lambda: list(ENHANCED_PIPELINE))
    status: str = "input_collecting"
    current_step_index: int = 0
    next_agent: Optional[str] = "input_collector"
    retry_count: int = 0
    max_retries: int = 3
    confirm_retry_count: int = 0
    max_confirmation_retries: int = 4
    checkpoint: Dict[str, Any] = field(default_factory=dict)
    user_input: Dict[str, Any] = field(default_factory=lambda: {
        "chunks": [], "is_complete": False, "completed_at": None
    })
    confirmation: Dict[str, Any] = field(default_factory=lambda: {
        "status": "pending", "selected_proposal": None,
        "user_skill_overrides": {}, "clarification_updates": [],
        "confirmed_at": None
    })
    created_at: str = ""
    updated_at: str = ""
    _snapshots: list = field(default_factory=list, repr=False)
    _file_path: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        self._enforce_invariants()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def _enforce_invariants(self):
        """保证 current_step_index 永远在合法范围内。"""
        if self.status in TERMINAL_STATES:
            self.current_step_index = len(self.pipeline) - 1
        elif self.status in self.pipeline:
            self.current_step_index = self.pipeline.index(self.status)
        else:
            self.current_step_index = min(
                max(0, self.current_step_index),
                len(self.pipeline) - 1
            )

    def advance_to(self, step: str, agent: Optional[str] = None) -> bool:
        """安全步进到指定阶段，越界或未知步骤返回 False。"""
        if step in TERMINAL_STATES:
            self.status = step
            self.next_agent = None
            self.current_step_index = len(self.pipeline) - 1
            self.updated_at = datetime.now().isoformat()
            return True
        if step not in self.pipeline:
            return False
        self.status = step
        self.current_step_index = self.pipeline.index(step)
        self.next_agent = agent
        self.updated_at = datetime.now().isoformat()
        return True

    def confirm_action(self, action: str, proposal: Optional[str] = None,
                       updates: Optional[List[Dict]] = None) -> str:
        """处理确认门决策，含回退限流。

        返回: "confirmed", "revised", "cancelled", "retry_exhausted", "error"
        """
        if action == "confirm":
            self.confirmation["status"] = "confirmed"
            self.confirmation["selected_proposal"] = proposal
            self.confirmation["confirmed_at"] = datetime.now().isoformat()
            self.advance_to("planning", "planner")
            return "confirmed"

        elif action == "revise":
            self.confirm_retry_count += 1
            if self.confirm_retry_count > self.max_confirmation_retries:
                return "retry_exhausted"
            self.confirmation["status"] = "revised"
            self.confirmation["clarification_updates"] = updates or []
            self.advance_to("requirement_optimizing", "requirement_optimizer")
            return "revised"

        elif action == "reject":
            self.status = "cancelled"
            self.next_agent = None
            self.current_step_index = len(self.pipeline) - 1
            self.updated_at = datetime.now().isoformat()
            return "cancelled"

        return "error"

    def snapshot(self, label: str = "") -> str:
        """创建快照，返回快照 ID。"""
        snap_id = f"snap_{len(self._snapshots)}_{datetime.now().strftime('%H%M%S')}"
        export = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        self._snapshots.append(_Snapshot(
            data=copy.deepcopy(export),
            timestamp=datetime.now().isoformat(),
            label=label or snap_id
        ))
        return snap_id

    def rollback(self, steps: int = 1) -> bool:
        """回滚到之前的快照，无快照返回 False。"""
        if not self._snapshots:
            return False
        idx = min(steps, len(self._snapshots)) - 1
        snap = self._snapshots.pop(idx)
        restored = snap.data
        for key in ("task_id", "pipeline", "status", "current_step_index",
                     "next_agent", "retry_count", "max_retries",
                     "checkpoint", "user_input", "confirmation",
                     "created_at", "updated_at"):
            if key in restored:
                setattr(self, key, restored[key])
        self._enforce_invariants()
        self.updated_at = datetime.now().isoformat()
        return True

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

    # --- 持久化 ---

    @classmethod
    def from_file(cls, path: str) -> "SafeState":
        """从 v2 state.json 加载，自动修复越界索引。"""
        p = Path(path)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        obj = cls(
            task_id=data.get("task_id", ""),
            pipeline=data.get("pipeline", list(ENHANCED_PIPELINE)),
            status=data.get("status", "input_collecting"),
            current_step_index=data.get("current_step_index", 0),
            next_agent=data.get("next_agent"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            checkpoint=data.get("checkpoint", {}),
            user_input=data.get("user_input", {}),
            confirmation=data.get("confirmation", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
        obj._file_path = str(p)
        return obj

    def save(self, path: Optional[str] = None) -> str:
        """保存为 v2 兼容的 state.json。"""
        target = Path(path or self._file_path or f"workflows/{self.task_id}/state.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        out = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        out.pop("_snapshots", None)
        out.pop("snapshots", None)
        out["confirm_retry_count"] = self.confirm_retry_count
        out["max_confirmation_retries"] = self.max_confirmation_retries

        # 原子写入
        import tempfile, os
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        os.replace(tmp, target)
        return str(target)

    def to_dict(self) -> Dict[str, Any]:
        """导出为 v2 兼容 dict。"""
        d = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        d.pop("_snapshots", None)
        d.pop("snapshots", None)
        return d