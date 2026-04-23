"""HeartbeatCheckpoint — 心跳检查点模块。

实现心跳检查点机制（对齐 Temporal heartbeat_details）。
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class HeartbeatCheckpoint:
    """心跳检查点（对齐 Temporal heartbeat_details）"""

    skill_name: str
    last_heartbeat_time: float = 0.0
    heartbeat_details: Dict[str, Any] = field(default_factory=dict)
    heartbeat_interval_seconds: float = 30.0
    missed_heartbeats: int = 0
    max_missed_heartbeats: int = 3
    artifacts_dir: Optional[Path] = None

    def __post_init__(self):
        if self.artifacts_dir is None:
            self.artifacts_dir = Path("artifacts")
        if isinstance(self.artifacts_dir, str):
            self.artifacts_dir = Path(self.artifacts_dir)

    def heartbeat(self, details: Optional[Dict[str, Any]] = None):
        """报告心跳（Skill 执行过程中定期调用）"""
        self.last_heartbeat_time = time.time()
        if details:
            self.heartbeat_details.update(details)
        self.missed_heartbeats = 0
        self._persist()

    def check_health(self) -> bool:
        """检查心跳是否正常"""
        elapsed = time.time() - self.last_heartbeat_time
        if elapsed > self.heartbeat_interval_seconds * (self.missed_heartbeats + 1):
            self.missed_heartbeats += 1
            if self.missed_heartbeats >= self.max_missed_heartbeats:
                return False
        return True

    def get_resume_context(self) -> Dict[str, Any]:
        """获取恢复上下文（崩溃后从此处恢复）"""
        return {
            "skill_name": self.skill_name,
            "last_heartbeat_time": self.last_heartbeat_time,
            "heartbeat_details": self.heartbeat_details,
            "can_resume": bool(self.heartbeat_details),
            "missed_heartbeats": self.missed_heartbeats,
        }

    def _persist(self):
        """持久化心跳状态到文件"""
        if self.artifacts_dir is None:
            return
        checkpoint_path = self.artifacts_dir / f"{self.skill_name}_heartbeat.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps(self.get_resume_context(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    @classmethod
    def load(cls, artifacts_dir: Path, skill_name: str) -> Optional['HeartbeatCheckpoint']:
        """从文件加载心跳检查点"""
        checkpoint_path = Path(artifacts_dir) / f"{skill_name}_heartbeat.json"
        if not checkpoint_path.exists():
            return None

        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            return cls(
                skill_name=data["skill_name"],
                last_heartbeat_time=data.get("last_heartbeat_time", 0.0),
                heartbeat_details=data.get("heartbeat_details", {}),
                missed_heartbeats=data.get("missed_heartbeats", 0),
                artifacts_dir=artifacts_dir,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @classmethod
    def create(cls, skill_name: str, heartbeat_interval_seconds: float = 30.0,
               artifacts_dir: Path = None) -> 'HeartbeatCheckpoint':
        """创建新的心跳检查点"""
        checkpoint = cls(
            skill_name=skill_name,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            artifacts_dir=artifacts_dir or Path("artifacts"),
        )
        checkpoint.heartbeat(details={"phase": "started", "timestamp": time.time()})
        return checkpoint


class HeartbeatManager:
    """心跳管理器 — 管理多个 Skill 的心跳"""

    def __init__(self, artifacts_dir: Path = None):
        self.artifacts_dir = artifacts_dir or Path("artifacts")
        self.checkpoints: Dict[str, HeartbeatCheckpoint] = {}

    def get_checkpoint(self, skill_name: str,
                       heartbeat_interval_seconds: float = 30.0) -> HeartbeatCheckpoint:
        """获取或创建心跳检查点"""
        if skill_name not in self.checkpoints:
            # 尝试加载已有的
            existing = HeartbeatCheckpoint.load(self.artifacts_dir, skill_name)
            if existing:
                self.checkpoints[skill_name] = existing
            else:
                self.checkpoints[skill_name] = HeartbeatCheckpoint.create(
                    skill_name=skill_name,
                    heartbeat_interval_seconds=heartbeat_interval_seconds,
                    artifacts_dir=self.artifacts_dir,
                )
        return self.checkpoints[skill_name]

    def heartbeat(self, skill_name: str, details: Optional[Dict[str, Any]] = None):
        """报告心跳"""
        checkpoint = self.get_checkpoint(skill_name)
        checkpoint.heartbeat(details)

    def check_all_health(self) -> Dict[str, bool]:
        """检查所有 Skill 的心跳健康状态"""
        return {
            skill_name: checkpoint.check_health()
            for skill_name, checkpoint in self.checkpoints.items()
        }

    def get_resume_contexts(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Skill 的恢复上下文"""
        return {
            skill_name: checkpoint.get_resume_context()
            for skill_name, checkpoint in self.checkpoints.items()
        }
