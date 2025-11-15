"""Configuration for Sandbox API"""

from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    """Sandbox API configuration with environment variable support"""

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
        ["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins"
    )

    # GitHub Configuration
    github_token: str = Field(..., description="GitHub personal access token")
    github_org: Optional[str] = Field(None, description="GitHub organization for sandbox repos")
    
    # Anthropic Configuration
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    
    # Redis Configuration
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")
    
    # Sandbox Configuration
    sandbox_ttl: int = Field(3600, description="Sandbox TTL in seconds (1 hour)")
    max_sandboxes_per_ip: int = Field(3, description="Max concurrent sandboxes per IP")
    workspace_base_path: str = Field("/tmp/seedgpt-sandboxes", description="Base path for sandbox workspaces")
    
    # Rate Limiting
    rate_limit_requests: int = Field(10, description="Max requests per window")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")


config = SandboxConfig()
