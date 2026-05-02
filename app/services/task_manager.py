"""Task lifecycle coordinator — wraps StateDB with web-layer logic."""

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.db import StateDB
from core.pipeline_def import PIPELINE, PIPELINE_STEPS

logger = logging.getLogger("app.task_manager")


class TaskManager:
    def __init__(self, workflows_dir: str, artifacts_dir: str):
        self.workflows_dir = Path(workflows_dir)
        self.artifacts_dir = Path(artifacts_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_db(self, task_id: str) -> StateDB:
        """Create a fresh StateDB per call for thread safety."""
        task_dir = str(self.workflows_dir / task_id)
        return StateDB(task_dir)

    def create_task(self, user_input: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        db = self._get_db(task_id)
        state = db.init_task(task_id)

        # Save user input with is_complete=True (web model: input collected upfront)
        user_input_json = json.dumps({
            "chunks": [{"seq": 0, "content": user_input}],
            "is_complete": True,
            **(metadata or {}),
        }, ensure_ascii=False)
        db.set_user_input(task_id, user_input_json)

        logger.info(f"Task created: {task_id}")
        return self._enrich_state(task_id, state)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = self._get_db(task_id)
            state = db.get_state(task_id)
            return self._enrich_state(task_id, state)
        except ValueError:
            return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        results = []
        for task_dir in sorted(self.workflows_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            db_path = task_dir / "state.db"
            if not db_path.exists():
                continue
            task_id = task_dir.name
            try:
                db = self._get_db(task_id)
                state = db.get_state(task_id)
                results.append(self._enrich_state(task_id, state))
            except Exception:
                continue
        return results

    def delete_task(self, task_id: str) -> bool:
        import shutil
        task_dir = self.workflows_dir / task_id
        if not task_dir.exists():
            return False
        shutil.rmtree(str(task_dir))
        logger.info(f"Task deleted: {task_id}")
        return True

    def save_confirmation(self, task_id: str, status: str, data: Optional[Dict] = None):
        """Write confirmation_json to state.db."""
        db = self._get_db(task_id)
        confirmation = {"status": status, **(data or {})}
        conn = db._connect()
        try:
            conn.execute(
                "UPDATE task_state SET confirmation_json=?, updated_at=? WHERE task_id=?",
                (json.dumps(confirmation, ensure_ascii=False), datetime.now().isoformat(), task_id),
            )
            conn.commit()
        finally:
            conn.close()
        logger.info(f"Confirmation saved for {task_id}: {status}")

    def prepare_for_run(self, task_id: str) -> Dict[str, Any]:
        """Pre-advance past completed needs_user stages."""
        db = self._get_db(task_id)
        state = db.get_state(task_id)
        status = state["status"]

        if status == "input_collecting":
            user_input = json.loads(state.get("user_input_json", "{}"))
            if user_input.get("is_complete"):
                db.update_status(task_id, "requirement_optimizing", "requirement_optimizer")
                logger.info(f"Pre-advanced {task_id}: input_collecting → requirement_optimizing")

        # Re-read after potential update
        state = db.get_state(task_id)
        return self._enrich_state(task_id, state)

    def get_proposals(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Read optimized_requirement.json from task artifacts."""
        task_dir = self.workflows_dir / task_id
        path = task_dir / "artifacts" / "optimized_requirement.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_task_dir(self, task_id: str) -> str:
        return str(self.workflows_dir / task_id)

    def _enrich_state(self, task_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Add computed fields to raw state, including per-stage status."""
        step_index = state.get("step_index", 0)
        current_status = state.get("status", "unknown")
        error = state.get("error", "")

        stages = {}
        for i, (name, agent, needs_user) in enumerate(PIPELINE):
            if i < step_index:
                stages[name] = {"status": "completed", "agent": agent}
            elif i == step_index:
                # 当前阶段的状态取决于整体 status
                if current_status in ("completed",):
                    stages[name] = {"status": "completed", "agent": agent}
                elif current_status in ("failed",):
                    stages[name] = {"status": "failed", "agent": agent}
                elif current_status in ("cancelled",):
                    stages[name] = {"status": "cancelled", "agent": agent}
                else:
                    stages[name] = {"status": "running", "agent": agent}
            else:
                stages[name] = {"status": "pending", "agent": agent}

        return {
            "task_id": task_id,
            "status": current_status,
            "current_stage": current_status,
            "stages": stages,
            "user_input_json": json.loads(state.get("user_input_json", "{}")),
            "confirmation_json": json.loads(state.get("confirmation_json", "{}")),
            "error": error if error else None,
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
        }
