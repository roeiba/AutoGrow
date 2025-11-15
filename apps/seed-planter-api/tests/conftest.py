"""
Pytest configuration and fixtures for Seed Planter API tests
"""

import os
import pytest
from typing import Generator
import httpx


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Get API base URL from environment or use default"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_client(api_base_url: str) -> Generator[httpx.Client, None, None]:
    """Create HTTP client for API testing"""
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_project_request() -> dict:
    """Sample project request payload"""
    return {
        "project_name": "test-blog",
        "project_description": "A simple blog about technology and innovation",
        "mode": "saas"
    }


@pytest.fixture
def sample_project_request_minimal() -> dict:
    """Minimal valid project request"""
    return {
        "project_name": "minimal-test",
        "project_description": "Minimal test project",
        "mode": "saas"
    }
