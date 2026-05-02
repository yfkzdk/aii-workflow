"""Pydantic request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    user_input: str = Field(..., min_length=1, description="User requirement description")
    metadata: Optional[Dict[str, Any]] = None


class TaskSummary(BaseModel):
    task_id: str
    status: str
    current_stage: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskDetail(BaseModel):
    task_id: str
    status: str
    current_stage: str
    stages: Dict[str, Any] = Field(default_factory=dict)
    user_input_json: Optional[Dict[str, Any]] = None
    confirmation_json: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConfirmRequest(BaseModel):
    action: str = Field(..., pattern="^(confirm|revise|reject)$")
    feedback: Optional[str] = None


class InputSupplement(BaseModel):
    content: str = Field(..., min_length=1)


class PipelineRunRequest(BaseModel):
    resume: bool = False


class HealthResponse(BaseModel):
    success: bool
    version: str
    uptime: str


class ArtifactInfo(BaseModel):
    name: str
    path: str
    size: int
    modified: Optional[str] = None


class ProposalResponse(BaseModel):
    task_id: str
    optimized: str
    original: Optional[str] = None
