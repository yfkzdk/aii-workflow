"""Task CRUD endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.auth import authenticate
from app.deps import get_task_manager
from app.models import TaskCreate, TaskDetail, TaskSummary
from app.services.task_manager import TaskManager

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskDetail, status_code=201)
async def create_task(body: TaskCreate, tm: TaskManager = Depends(get_task_manager), _auth=Depends(authenticate)):
    task = tm.create_task(body.user_input, body.metadata)
    return task


@router.get("/tasks", response_model=List[TaskSummary])
async def list_tasks(tm: TaskManager = Depends(get_task_manager), _auth=Depends(authenticate)):
    tasks = tm.list_tasks()
    return [
        TaskSummary(
            task_id=t["task_id"],
            status=t["status"],
            current_stage=t["current_stage"],
            created_at=t.get("created_at"),
            updated_at=t.get("updated_at"),
        )
        for t in tasks
    ]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str, tm: TaskManager = Depends(get_task_manager), _auth=Depends(authenticate)):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, tm: TaskManager = Depends(get_task_manager), _auth=Depends(authenticate)):
    if not tm.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
