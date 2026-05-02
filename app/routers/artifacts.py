"""Artifact browsing endpoints."""

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import authenticate
from app.deps import get_task_manager
from app.models import ArtifactInfo
from app.services.task_manager import TaskManager

router = APIRouter(tags=["artifacts"])


def _format_mtime(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).isoformat()


@router.get("/tasks/{task_id}/artifacts", response_model=List[ArtifactInfo])
async def list_artifacts(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager),
    _auth=Depends(authenticate),
):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    artifacts_dir = Path(tm.get_task_dir(task_id)) / "artifacts"
    task_dir = Path(tm.get_task_dir(task_id))

    result = []

    # 包含任务根目录下的产物文件
    for name in ["AI_WORKFLOW_LOG.md"]:
        f = task_dir / name
        if f.is_file():
            result.append(ArtifactInfo(
                name=name,
                path=f"/api/tasks/{task_id}/artifacts/{name}",
                size=f.stat().st_size,
                modified=_format_mtime(f.stat().st_mtime),
            ))

    if artifacts_dir.exists():
        for f in sorted(artifacts_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(artifacts_dir)
                stat = f.stat()
                result.append(ArtifactInfo(
                    name=str(rel),
                    path=f"/api/tasks/{task_id}/artifacts/{rel}",
                    size=stat.st_size,
                    modified=_format_mtime(stat.st_mtime),
                ))

    return result


@router.get("/tasks/{task_id}/artifacts/{file_path:path}")
async def get_artifact_file(
    task_id: str,
    file_path: str,
    tm: TaskManager = Depends(get_task_manager),
    _auth=Depends(authenticate),
):
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 先检查 artifacts/ 子目录
    full_path = Path(tm.get_task_dir(task_id)) / "artifacts" / file_path
    if not full_path.exists():
        # 再检查任务根目录
        full_path = Path(tm.get_task_dir(task_id)) / file_path

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # 安全检查：确保路径没有逃逸出任务目录
    task_dir = Path(tm.get_task_dir(task_id)).resolve()
    if not str(full_path.resolve()).startswith(str(task_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        str(full_path),
        filename=full_path.name,
        media_type="application/octet-stream",
    )