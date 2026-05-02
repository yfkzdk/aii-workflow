"""FastAPI dependency injection."""

from typing import Optional

from app.config import settings
from app.services.event_bus import EventBus
from app.services.task_manager import TaskManager


_event_bus: Optional[EventBus] = None
_task_manager: Optional[TaskManager] = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(settings.workflows_dir, settings.artifacts_dir)
    return _task_manager
