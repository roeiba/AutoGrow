"""Data models for Seed Planter API"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProjectMode(str, Enum):
    """Project deployment mode"""
    SAAS = "saas"  # SeedGPT's accounts
    USER_ENV = "user_env"  # User's own accounts


class DeploymentType(str, Enum):
    """Project deployment type"""
    GITHUB_PAGES = "github_pages"
    DOCKER_GCP = "docker_gcp"
    NONE = "none"


class ProjectStatus(str, Enum):
    """Project planting status"""
    INITIALIZING = "initializing"
    CREATING_ORG = "creating_org"
    FORKING_TEMPLATE = "forking_template"
    CUSTOMIZING_PROJECT = "customizing_project"
    CREATING_GCP_PROJECT = "creating_gcp_project"
    DEPLOYING = "deploying"
    CREATING_ISSUES = "creating_issues"
    COMPLETED = "completed"
    FAILED = "failed"


class PlantSeedRequest(BaseModel):
    """Request to plant a new project seed"""
    project_name: str = Field(..., min_length=3, max_length=50, description="Project name (will be org name)")
    project_description: str = Field(..., min_length=10, max_length=1000, description="Project description/prompt")
    user_email: Optional[str] = Field(None, description="Optional user email for notifications")
    mode: ProjectMode = Field(ProjectMode.SAAS, description="Deployment mode")


class PlantSeedResponse(BaseModel):
    """Response after planting seed"""
    project_id: str = Field(..., description="Unique project identifier")
    status: ProjectStatus = Field(..., description="Current project status")
    created_at: datetime = Field(..., description="Creation timestamp")
    websocket_url: str = Field(..., description="WebSocket URL for real-time updates")
    estimated_completion_time: int = Field(..., description="Estimated time in seconds")


class ProjectProgress(BaseModel):
    """Progress update for project planting"""
    project_id: str
    status: ProjectStatus
    message: str
    progress_percent: int = Field(ge=0, le=100)
    timestamp: datetime
    org_url: Optional[str] = None
    repo_url: Optional[str] = None
    deployment_url: Optional[str] = None
    gcp_project_id: Optional[str] = None


class ProjectDetails(BaseModel):
    """Detailed project information"""
    project_id: str
    project_name: str
    status: ProjectStatus
    project_description: str
    created_at: datetime
    mode: ProjectMode
    
    # GitHub info
    org_name: Optional[str] = None
    org_url: Optional[str] = None
    repo_url: Optional[str] = None
    
    # GCP info
    gcp_project_id: Optional[str] = None
    
    # Deployment info
    deployment_type: Optional[DeploymentType] = None
    deployment_url: Optional[str] = None
    
    # Progress
    issues_created: int = 0
    is_deployed: bool = False
    error_message: Optional[str] = None
    
    # Ownership
    can_transfer: bool = True
    owner_email: Optional[str] = None


class ProjectListResponse(BaseModel):
    """List of planted projects"""
    projects: list[ProjectDetails]
    total: int
