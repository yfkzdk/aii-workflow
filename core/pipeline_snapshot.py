"""PipelineSnapshot — 流水线快照模块。

实现流水线快照与恢复机制（对齐 Haystack PipelineSnapshot）。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PipelineSnapshot:
    """流水线快照（对齐 Haystack PipelineSnapshot）"""

    # 执行状态
    stage: str
    completed_skills: List[str] = field(default_factory=list)
    skill_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skill_run_counts: Dict[str, int] = field(default_factory=dict)

    # 优先级队列状态
    pending_skills: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    trace_id: str = ""
    config_version: str = ""
    timestamp: str = ""
    snapshot_version: str = "1.0"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "snapshot_version": self.snapshot_version,
            "stage": self.stage,
            "completed_skills": self.completed_skills,
            "skill_results": self.skill_results,
            "skill_run_counts": self.skill_run_counts,
            "pending_skills": self.pending_skills,
            "trace_id": self.trace_id,
            "config_version": self.config_version,
            "timestamp": self.timestamp,
        }

    def save(self, path: Path):
        """保存快照到文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> Optional['PipelineSnapshot']:
        """从文件加载快照"""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                stage=data["stage"],
                completed_skills=data.get("completed_skills", []),
                skill_results=data.get("skill_results", {}),
                skill_run_counts=data.get("skill_run_counts", {}),
                pending_skills=data.get("pending_skills", []),
                trace_id=data.get("trace_id", ""),
                config_version=data.get("config_version", ""),
                timestamp=data.get("timestamp", ""),
                snapshot_version=data.get("snapshot_version", "1.0"),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @classmethod
    def create(cls, stage: str, trace_id: str = "", config_version: str = "") -> 'PipelineSnapshot':
        """创建新的流水线快照"""
        return cls(
            stage=stage,
            trace_id=trace_id,
            config_version=config_version,
            timestamp=datetime.now().isoformat(),
        )


class PipelineSnapshotManager:
    """流水线快照管理器"""

    def __init__(self, snapshot_dir: Path = None):
        self.snapshot_dir = snapshot_dir or Path("artifacts/snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: PipelineSnapshot, label: str = "") -> Path:
        """保存快照"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stage = snapshot.stage or "unknown"
        filename = f"snapshot_{stage}_{timestamp}"
        if label:
            filename += f"_{label}"
        filename += ".json"

        path = self.snapshot_dir / filename
        snapshot.save(path)
        return path

    def load_latest_snapshot(self, trace_id: str = None) -> Optional[PipelineSnapshot]:
        """加载最新快照"""
        snapshots = sorted(
            self.snapshot_dir.glob("snapshot_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        if not snapshots:
            return None

        for snapshot_path in snapshots:
            snapshot = PipelineSnapshot.load(snapshot_path)
            if snapshot:
                if trace_id and snapshot.trace_id != trace_id:
                    continue
                return snapshot

        return None

    def load_snapshot_by_stage(self, stage: str) -> Optional[PipelineSnapshot]:
        """加载指定阶段的最新快照"""
        snapshots = sorted(
            self.snapshot_dir.glob(f"snapshot_{stage}_*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        if not snapshots:
            return None
        return PipelineSnapshot.load(snapshots[0])

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        result = []
        for snapshot_path in sorted(self.snapshot_dir.glob("snapshot_*.json")):
            snapshot = PipelineSnapshot.load(snapshot_path)
            if snapshot:
                result.append({
                    "path": str(snapshot_path),
                    "stage": snapshot.stage,
                    "timestamp": snapshot.timestamp,
                    "trace_id": snapshot.trace_id,
                    "completed_count": len(snapshot.completed_skills),
                })
        return result

    def cleanup_old_snapshots(self, max_age_days: int = 7, max_count: int = 100):
        """清理旧快照"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        snapshots = sorted(
            self.snapshot_dir.glob("snapshot_*.json"),
            key=lambda f: f.stat().st_mtime
        )

        # 按数量清理
        while len(snapshots) > max_count:
            snapshots.pop(0).unlink()

        # 按时间清理
        for snapshot_path in snapshots:
            mtime = datetime.fromtimestamp(snapshot_path.stat().st_mtime)
            if mtime < cutoff:
                snapshot_path.unlink()
