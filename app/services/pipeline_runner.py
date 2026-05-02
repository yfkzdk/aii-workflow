"""PipelineRunner — runs Orchestrator in a background thread, emits events to EventBus."""

import json
import logging
import threading
from typing import Optional

from app.services.event_bus import EventBus, PipelineEvent
from core.orchestrator import Orchestrator
from core.pipeline_def import PIPELINE_STEPS

logger = logging.getLogger("app.pipeline_runner")


class PipelineRunner:
    def __init__(self, task_id: str, task_dir: str, project_root: str, event_bus: EventBus):
        self.task_id = task_id
        self.task_dir = task_dir
        self.project_root = project_root
        self.event_bus = event_bus
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self):
        with self._lock:
            if self.is_running():
                return
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        try:
            self._emit("pipeline_started", "orchestrator")
            orch = Orchestrator(self.task_dir, self.task_id, project_root=self.project_root)

            # Hook into orchestrator to emit stage events
            original_update_status = orch.db.update_status
            last_status = [None]

            def tracked_update_status(task_id, new_status, next_agent=None):
                old_status = last_status[0]
                result = original_update_status(task_id, new_status, next_agent)
                last_status[0] = new_status

                # Emit stage transition event
                if new_status in PIPELINE_STEPS:
                    self._emit("stage_changed", new_status, {
                        "from": old_status,
                        "to": new_status,
                    })
                elif new_status in ("completed", "cancelled", "failed"):
                    self._emit("stage_changed", new_status, {
                        "from": old_status,
                        "to": new_status,
                    })
                return result

            orch.db.update_status = tracked_update_status
            last_status[0] = orch.db.get_state(self.task_id).get("status")

            # Run the orchestrator loop
            result = orch.run()

            # Distinguish pause vs completion
            if result.get("waiting_for"):
                # Pipeline paused for user input (confirmation gate)
                self._emit("pipeline_paused", result.get("status", "unknown"), {
                    "waiting_for": result.get("waiting_for"),
                    "step_index": result.get("step_index"),
                })
            elif result.get("status") == "failed":
                self._emit("pipeline_error", "orchestrator", {
                    "error": result.get("error", "Unknown error"),
                    "step": result.get("step"),
                })
            else:
                self._emit("pipeline_completed", "orchestrator", {"result": str(result)})
        except Exception as e:
            logger.error(f"Pipeline error for {self.task_id}: {e}", exc_info=True)
            self._emit("pipeline_error", "orchestrator", {"error": str(e)})
        finally:
            self._running = False

    def _emit(self, event_type: str, stage: str, data: Optional[dict] = None):
        self.event_bus.emit(self.task_id, PipelineEvent(
            type=event_type,
            task_id=self.task_id,
            stage=stage,
            data=data,
        ))
