"""Pipeline control endpoints — run, confirm, input, proposals."""

import json
import logging
import threading

from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException

from app.auth import authenticate
from app.config import settings
from app.deps import get_event_bus, get_task_manager
from app.models import ConfirmRequest, InputSupplement, PipelineRunRequest, ProposalResponse
from app.services.event_bus import EventBus, PipelineEvent
from app.services.pipeline_runner import PipelineRunner
from app.services.task_manager import TaskManager

logger = logging.getLogger("app.pipeline")

router = APIRouter(tags=["pipeline"])

_pipeline_runners: dict = {}
_runners_lock = threading.Lock()


def _get_or_create_runner(task_id: str, tm: TaskManager, eb: EventBus) -> PipelineRunner:
    with _runners_lock:
        if task_id not in _pipeline_runners:
            _pipeline_runners[task_id] = PipelineRunner(
                task_id=task_id,
                task_dir=tm.get_task_dir(task_id),
                project_root=settings.project_root,
                event_bus=eb,
            )
        return _pipeline_runners[task_id]


@router.post("/tasks/{task_id}/run", status_code=202)
async def run_pipeline(
    task_id: str,
    body: Optional[PipelineRunRequest] = None,
    tm: TaskManager = Depends(get_task_manager),
    eb: EventBus = Depends(get_event_bus),
    _auth=Depends(authenticate),
):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Task already {task['status']}")

    runner = _get_or_create_runner(task_id, tm, eb)
    if runner.is_running():
        raise HTTPException(status_code=409, detail="Pipeline already running for this task")

    # Pre-advance past completed needs_user stages
    tm.prepare_for_run(task_id)

    runner.start()
    return {"task_id": task_id, "status": "running", "message": "Pipeline started"}


@router.post("/tasks/{task_id}/confirm")
async def confirm_task(
    task_id: str,
    body: ConfirmRequest,
    tm: TaskManager = Depends(get_task_manager),
    eb: EventBus = Depends(get_event_bus),
    _auth=Depends(authenticate),
):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] != "confirmation":
        raise HTTPException(status_code=409, detail="Task is not at confirmation stage")

    # Save confirmation to DB
    tm.save_confirmation(task_id, "confirmed" if body.action == "confirm" else body.action,
                         {"feedback": body.feedback} if body.feedback else None)

    # Use Orchestrator's handle_confirmation for proper state transitions
    from core.orchestrator import Orchestrator
    orch = Orchestrator(tm.get_task_dir(task_id), task_id, project_root=settings.project_root)
    result = orch.handle_confirmation(body.action)

    eb.emit(task_id, PipelineEvent(
        type="confirmation_handled",
        task_id=task_id,
        stage="confirmation",
        data={"action": body.action, "result": result},
    ))

    # If confirmed, auto-resume pipeline
    if body.action == "confirm":
        runner = _get_or_create_runner(task_id, tm, eb)
        if not runner.is_running():
            runner.start()

    return {"task_id": task_id, "action": body.action, "result": result}


@router.post("/tasks/{task_id}/input")
async def submit_input(
    task_id: str,
    body: InputSupplement,
    tm: TaskManager = Depends(get_task_manager),
    eb: EventBus = Depends(get_event_bus),
    _auth=Depends(authenticate),
):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from core.orchestrator import Orchestrator
    orch = Orchestrator(tm.get_task_dir(task_id), task_id, project_root=settings.project_root)
    result = orch.handle_user_input(body.content)

    # Mark input as complete
    db = tm._get_db(task_id)
    state = db.get_state(task_id)
    user_input = json.loads(state.get("user_input_json", "{}"))
    user_input["is_complete"] = True
    db.set_user_input(task_id, json.dumps(user_input, ensure_ascii=False))

    eb.emit(task_id, PipelineEvent(
        type="input_submitted",
        task_id=task_id,
        stage="input_collecting",
        data={"content_length": len(body.content)},
    ))

    return {"task_id": task_id, "result": "input_saved"}


@router.get("/tasks/{task_id}/proposals", response_model=ProposalResponse)
async def get_proposals(task_id: str, tm: TaskManager = Depends(get_task_manager), _auth=Depends(authenticate)):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    proposals = tm.get_proposals(task_id)
    if not proposals:
        raise HTTPException(status_code=404, detail="No proposals found")

    # Return the full proposal object as a formatted string
    optimized_text = json.dumps(proposals, ensure_ascii=False, indent=2)
    chunks = task.get("user_input_json", {}).get("chunks", [])
    original = chunks[0].get("content") if chunks else None

    return ProposalResponse(
        task_id=task_id,
        optimized=optimized_text,
        original=original,
    )


@router.get("/pipeline")
async def get_pipeline_def():
    from core.pipeline_def import PIPELINE
    return {
        "stages": [
            {"name": name, "agent": agent, "needs_user": needs_user}
            for name, agent, needs_user in PIPELINE
        ]
    }