"""Configuration for Seed Planter API"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SeedPlanterConfig(BaseSettings):
    """Seed Planter API configuration with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    api_host: str = Field("0.0.0.0", description="API host")
    api_port: int = Field(8000, description="API port")
    api_debug: bool = Field(False, description="Debug mode")
    cors_origins: list[str] = Field(
        [
            "http://localhost:3000", 
            "http://localhost:5173",
            "https://seed-planter-frontend-1068119864554.us-central1.run.app",
            "*"  # Allow all origins for now (can be restricted later)
        ],
        description="CORS allowed origins"
    )

    # GitHub Configuration (SeedGPT's account for SaaS mode)
    github_token: str = Field(..., description="GitHub personal access token")
    github_username: str = Field(..., description="GitHub username (for SaaS mode)")
    seedgpt_template_repo: str = Field(
        "roeiba/SeedGPT",
        description="SeedGPT template repository to fork"
    )
    
    # GitHub OAuth App Configuration
    github_oauth_client_id: str = Field("Ov23liv5I7Rn6Fh2HJQh", description="GitHub OAuth App Client ID")
    github_oauth_client_secret: Optional[str] = Field(None, description="GitHub OAuth App Client Secret")
    
    # Anthropic Configuration
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    
    # Google Cloud Configuration (SeedGPT's account for SaaS mode)
    gcp_project_id: str = Field("seedgpt", description="Base GCP project ID")
    gcp_credentials_path: Optional[str] = Field(None, description="Path to GCP service account JSON")
    gcp_region: str = Field("us-central1", description="Default GCP region")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")
    
    # Project Configuration
    max_projects_per_ip: int = Field(5, description="Max projects per IP in SaaS mode")
    workspace_base_path: str = Field("/tmp/seedgpt-projects", description="Base path for project workspaces")
    
    # Deployment Configuration
    docker_registry: str = Field("gcr.io", description="Docker registry for GCP")
    min_instances: int = Field(0, description="Minimum Cloud Run instances")
    max_instances: int = Field(10, description="Maximum Cloud Run instances")
    
    # Rate Limiting
    rate_limit_requests: int = Field(10, description="Max requests per window")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")


config = SeedPlanterConfig()
