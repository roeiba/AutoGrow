"""Data models for Sandbox API"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SandboxStatus(str, Enum):
    """Sandbox execution status"""
    INITIALIZING = "initializing"
    CREATING_REPO = "creating_repo"
    GENERATING_STRUCTURE = "generating_structure"
    CREATING_ISSUES = "creating_issues"
    CREATING_PR = "creating_pr"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class SandboxRequest(BaseModel):
    """Request to create a new sandbox"""
    project_idea: str = Field(..., min_length=10, max_length=500, description="Project idea description")
    user_email: Optional[str] = Field(None, description="Optional user email for notifications")


class SandboxResponse(BaseModel):
    """Response after creating sandbox"""
    sandbox_id: str = Field(..., description="Unique sandbox identifier")
    status: SandboxStatus = Field(..., description="Current sandbox status")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    websocket_url: str = Field(..., description="WebSocket URL for real-time updates")


class SandboxProgress(BaseModel):
    """Progress update for sandbox execution"""
    sandbox_id: str
    status: SandboxStatus
    message: str
    progress_percent: int = Field(ge=0, le=100)
    timestamp: datetime
    repo_url: Optional[str] = None
    issue_url: Optional[str] = None
    pr_url: Optional[str] = None


class SandboxDetails(BaseModel):
    """Detailed sandbox information"""
    sandbox_id: str
    status: SandboxStatus
    project_idea: str
    created_at: datetime
    expires_at: datetime
    repo_url: Optional[str] = None
    repo_name: Optional[str] = None
    issues_created: int = 0
    pr_created: bool = False
    pr_url: Optional[str] = None
    error_message: Optional[str] = None


class SandboxListResponse(BaseModel):
    """List of active sandboxes"""
    sandboxes: list[SandboxDetails]
    total: int
